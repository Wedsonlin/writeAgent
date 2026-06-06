"""A2A-compatible internal delegation schema."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from artifacts.schemas import ArtifactRef


class DelegationRequest(BaseModel):
    receiver_agent_id: str | None = None
    capability: str
    instruction: str
    input_artifacts: list[ArtifactRef] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    context_id: str | None = None
    task_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DelegationResult(BaseModel):
    status: Literal["ok", "failed", "blocked"]
    summary: str
    output_artifacts: list[ArtifactRef] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)
    trace_id: str | None = None
    raw_response: dict[str, Any] | None = None
