"""Lightweight local Agent-to-Agent delegation protocol types."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass
class SubAgentSpec:
    subagent_id: str
    parent_agent_id: str
    role: str
    task: str
    input_keys: list[str]
    output_key: str
    skill_context: list[str] = field(default_factory=list)
    prompt_refs: list[str] = field(default_factory=list)
    output_schema: str | dict[str, Any] | None = None
    allowed_tools: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    model_policy: dict[str, Any] = field(default_factory=dict)
    write_policy: Literal["return_only", "write_intermediate"] = "write_intermediate"


@dataclass
class SubAgentResult:
    subagent_id: str
    parent_agent_id: str
    status: Literal["completed", "failed", "needs_input", "blocked"]
    output_key: str | None
    result_summary: str
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    needs_followup: bool = False
    followup_question: str | None = None
    usage: dict[str, Any] = field(default_factory=dict)


@dataclass
class SubAgentTrace:
    subagent_id: str
    parent_agent_id: str
    role: str
    task: str
    input_keys: list[str]
    output_key: str
    skill_context: list[str]
    prompt_refs: list[str]
    allowed_tools: list[str]
    constraints: dict[str, Any]
    status: str
    started_at: str
    ended_at: str | None = None
    llm_call_ids: list[str] = field(default_factory=list)
    tool_call_ids: list[str] = field(default_factory=list)
    result_summary: str | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class A2AArtifact:
    kind: str
    uri: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class A2AError:
    code: str
    message: str
    detail: dict[str, Any] = field(default_factory=dict)


def to_dict(value: Any) -> dict[str, Any]:
    """Convert a protocol dataclass to a plain JSON-serializable dict."""
    return asdict(value)


__all__ = [
    "A2AArtifact",
    "A2AError",
    "SubAgentResult",
    "SubAgentSpec",
    "SubAgentTrace",
    "to_dict",
]
