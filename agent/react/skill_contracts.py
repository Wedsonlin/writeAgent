"""Skill contract loading and rendering helpers.

Contracts are deterministic metadata consumed by the Main Agent prompt. They
describe when a Skill is runnable and which SubAgent-produced intermediates are
needed before invoking the deterministic Skill script.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SubAgentPrerequisite:
    """One intermediate that should be produced by a delegated SubAgent."""

    output_key: str
    role: str
    task: str
    input_keys: list[str] = field(default_factory=list)
    output_schema: str | dict[str, Any] | None = None
    success_criteria: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SkillContract:
    """Validated Skill orchestration metadata."""

    required_state_keys: list[str] = field(default_factory=list)
    required_intermediate_keys: list[str] = field(default_factory=list)
    formal_outputs: list[str] = field(default_factory=list)
    subagent_prerequisites: list[SubAgentPrerequisite] = field(default_factory=list)
    common_errors: list[str] = field(default_factory=list)
    output_schemas: dict[str, Any] = field(default_factory=dict)
    source: str = "default"

    @property
    def is_empty(self) -> bool:
        return not any(
            (
                self.required_state_keys,
                self.required_intermediate_keys,
                self.formal_outputs,
                self.subagent_prerequisites,
                self.common_errors,
                self.output_schemas,
            )
        )

    def to_prompt_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.required_state_keys:
            payload["required_state_keys"] = self.required_state_keys
        if self.required_intermediate_keys:
            payload["required_intermediate_keys"] = self.required_intermediate_keys
        if self.formal_outputs:
            payload["formal_outputs"] = self.formal_outputs
        if self.subagent_prerequisites:
            payload["subagent_prerequisites"] = [
                {
                    "role": item.role,
                    "output_key": item.output_key,
                    "input_keys": item.input_keys,
                    "output_schema": _schema_summary(item.output_schema),
                    "task": item.task,
                    "success_criteria": item.success_criteria,
                }
                for item in self.subagent_prerequisites
            ]
        if self.common_errors:
            payload["common_errors"] = self.common_errors
        return payload


def load_skill_contract(skill_dir: Path, frontmatter: dict[str, Any] | None = None) -> SkillContract:
    """Load explicit or generated contract metadata for one Skill directory."""
    skill_dir = Path(skill_dir)
    for filename, source in (
        ("contract.json", "contract.json"),
        ("contract.generated.json", "contract.generated.json"),
    ):
        path = skill_dir / filename
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return SkillContract(source=f"invalid:{source}")
        return _contract_from_payload(payload, source=source)

    frontmatter_contract = (frontmatter or {}).get("skill_contract")
    if isinstance(frontmatter_contract, dict):
        return _contract_from_payload(frontmatter_contract, source="frontmatter.skill_contract")
    return SkillContract()


def render_contract_for_prompt(contract: SkillContract) -> list[str]:
    """Render contract metadata as compact prompt lines."""
    if contract.is_empty:
        return []
    payload = contract.to_prompt_dict()
    lines = ["  contract:"]
    if payload.get("required_state_keys"):
        lines.append(f"    required_state_keys: {json.dumps(payload['required_state_keys'], ensure_ascii=False)}")
    if payload.get("required_intermediate_keys"):
        lines.append(
            f"    required_intermediate_keys: {json.dumps(payload['required_intermediate_keys'], ensure_ascii=False)}"
        )
    if payload.get("formal_outputs"):
        lines.append(f"    formal_outputs: {json.dumps(payload['formal_outputs'], ensure_ascii=False)}")
    for item in payload.get("subagent_prerequisites", []):
        lines.append(f"    subagent_prerequisite: role={item['role']} output_key={item['output_key']}")
        if item.get("input_keys"):
            lines.append(f"      input_keys: {json.dumps(item['input_keys'], ensure_ascii=False)}")
        if item.get("output_schema"):
            lines.append(f"      output_schema: {json.dumps(item['output_schema'], ensure_ascii=False)}")
        if item.get("success_criteria"):
            lines.append(f"      success_criteria: {json.dumps(item['success_criteria'], ensure_ascii=False)}")
    if payload.get("common_errors"):
        lines.append(f"    common_errors: {json.dumps(payload['common_errors'], ensure_ascii=False)}")
    return lines


def _contract_from_payload(payload: Any, *, source: str) -> SkillContract:
    if not isinstance(payload, dict):
        return SkillContract(source=f"invalid:{source}")
    subagents = []
    for raw in _list_dict(payload.get("subagent_prerequisites")):
        output_key = str(raw.get("output_key") or "").strip()
        role = str(raw.get("role") or "").strip()
        task = str(raw.get("task") or "").strip()
        if not output_key or not role or not task:
            continue
        subagents.append(
            SubAgentPrerequisite(
                output_key=output_key,
                role=role,
                task=task,
                input_keys=_list_str(raw.get("input_keys")),
                output_schema=raw.get("output_schema"),
                success_criteria=_list_str(raw.get("success_criteria")),
            )
        )
    output_schemas = payload.get("output_schemas")
    return SkillContract(
        required_state_keys=_list_str(payload.get("required_state_keys")),
        required_intermediate_keys=_list_str(payload.get("required_intermediate_keys")),
        formal_outputs=_list_str(payload.get("formal_outputs")),
        subagent_prerequisites=subagents,
        common_errors=_list_str(payload.get("common_errors")),
        output_schemas=output_schemas if isinstance(output_schemas, dict) else {},
        source=source,
    )


def _schema_summary(schema: str | dict[str, Any] | None) -> str | dict[str, Any] | None:
    if not isinstance(schema, dict):
        return schema
    summary: dict[str, Any] = {}
    for key in ("type", "required", "properties", "additionalProperties"):
        if key in schema:
            summary[key] = schema[key]
    return summary or schema


def _list_str(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _list_dict(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


__all__ = [
    "SkillContract",
    "SubAgentPrerequisite",
    "load_skill_contract",
    "render_contract_for_prompt",
]
