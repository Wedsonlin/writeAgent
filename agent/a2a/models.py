"""Pydantic models for the local A2A delegation protocol."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from .types import A2AArtifact, A2AError, SubAgentResult, SubAgentSpec, SubAgentTrace


class A2AArtifactModel(BaseModel):
    kind: str
    uri: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dataclass(self) -> A2AArtifact:
        return A2AArtifact(**_dump_model(self))


class A2AErrorModel(BaseModel):
    code: str
    message: str
    detail: dict[str, Any] = Field(default_factory=dict)

    def to_dataclass(self) -> A2AError:
        return A2AError(**_dump_model(self))


class SubAgentSpecModel(BaseModel):
    subagent_id: str
    parent_agent_id: str
    role: str
    task: str
    input_keys: list[str]
    output_key: str
    skill_context: list[str] = Field(default_factory=list)
    prompt_refs: list[str] = Field(default_factory=list)
    output_schema: str | dict[str, Any] | None = None
    allowed_tools: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    model_policy: dict[str, Any] = Field(default_factory=dict)
    write_policy: Literal["return_only", "write_intermediate"] = "write_intermediate"

    @classmethod
    def from_any(cls, value: Any) -> "SubAgentSpecModel":
        return _validate_model(cls, _to_dict(value))

    def to_dataclass(self) -> SubAgentSpec:
        return SubAgentSpec(**_dump_model(self))


class SubAgentResultModel(BaseModel):
    subagent_id: str
    parent_agent_id: str
    status: Literal["completed", "failed", "needs_input", "blocked"]
    output_key: str | None
    result_summary: str
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    needs_followup: bool = False
    followup_question: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_any(cls, value: Any) -> "SubAgentResultModel":
        return _validate_model(cls, _to_dict(value))

    def to_dataclass(self) -> SubAgentResult:
        return SubAgentResult(**_dump_model(self))


class SubAgentTraceModel(BaseModel):
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
    llm_call_ids: list[str] = Field(default_factory=list)
    tool_call_ids: list[str] = Field(default_factory=list)
    result_summary: str | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def from_any(cls, value: Any) -> "SubAgentTraceModel":
        return _validate_model(cls, _to_dict(value))

    def to_dataclass(self) -> SubAgentTrace:
        return SubAgentTrace(**_dump_model(self))


def _to_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return value
    raise TypeError(f"Cannot convert A2A value to dict: {type(value).__name__}")


def _dump_model(value: BaseModel) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()  # type: ignore[no-any-return]
    return value.dict()


def _validate_model(model_type: type[BaseModel], value: dict[str, Any]) -> Any:
    if hasattr(model_type, "model_validate"):
        return model_type.model_validate(value)
    return model_type.parse_obj(value)


__all__ = [
    "A2AArtifactModel",
    "A2AErrorModel",
    "SubAgentResultModel",
    "SubAgentSpecModel",
    "SubAgentTraceModel",
]
