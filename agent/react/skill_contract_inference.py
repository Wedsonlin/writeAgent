"""Scaffold for cached LLM-assisted Skill contract inference.

This module intentionally does not run in the normal SkillRegistry hot path.
It builds a deterministic prompt that can be sent to an LLM by a future command
or reviewed manually, then saved as ``contract.generated.json``.
"""

from __future__ import annotations

import json
from pathlib import Path


def build_contract_inference_prompt(skill_dir: Path, *, schemas_dir: Path | None = None) -> str:
    """Build a prompt for inferring a SkillContract JSON document."""
    skill_dir = Path(skill_dir)
    skill_md = _read_optional(skill_dir / "SKILL.md")
    run_py = _read_optional(skill_dir / "scripts" / "run.py", limit=30000)
    schemas = _collect_schemas(schemas_dir) if schemas_dir is not None else {}
    payload = {
        "task": "Infer a deterministic writeAgent SkillContract JSON document.",
        "rules": [
            "Return JSON only.",
            "Do not invent runtime behavior not supported by SKILL.md or scripts/run.py.",
            "Prefer explicit required_state_keys and required_intermediate_keys.",
            "For each missing intermediate, propose a subagent_prerequisite with output_key, input_keys, task, and output_schema.",
            "If uncertain, leave fields empty rather than hallucinating.",
        ],
        "target_schema": {
            "required_state_keys": ["state.key"],
            "required_intermediate_keys": ["intermediate.path"],
            "formal_outputs": ["formal_output_key"],
            "subagent_prerequisites": [
                {
                    "role": "specialist role",
                    "task": "specific local task",
                    "input_keys": ["authorized.state.key"],
                    "output_key": "intermediate.path",
                    "output_schema": {"type": "object", "required": []},
                    "success_criteria": ["criterion"],
                }
            ],
            "common_errors": ["known recoverable error"],
            "output_schemas": {},
        },
        "skill_md": skill_md,
        "run_py": run_py,
        "schemas": schemas,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def generated_contract_path(skill_dir: Path) -> Path:
    return Path(skill_dir) / "contract.generated.json"


def _collect_schemas(schemas_dir: Path | None) -> dict[str, str]:
    if schemas_dir is None or not Path(schemas_dir).exists():
        return {}
    out: dict[str, str] = {}
    for path in sorted(Path(schemas_dir).glob("*.json")):
        out[path.name] = _read_optional(path, limit=20000)
    return out


def _read_optional(path: Path, *, limit: int = 50000) -> str:
    if not path.exists() or not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:limit]


__all__ = ["build_contract_inference_prompt", "generated_contract_path"]
