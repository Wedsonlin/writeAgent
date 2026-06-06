"""Main Agent delegation tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from artifacts.schemas import ArtifactRef
from delegation.runtime import DelegationRuntime
from delegation.schema import DelegationRequest


class DelegateToAgentInput(BaseModel):
    receiver_agent_id: str | None = None
    capability: str
    instruction: str
    input_artifacts: list[ArtifactRef] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    context_id: str | None = None
    task_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def delegate_to_agent(runtime: DelegationRuntime, **kwargs: Any) -> dict[str, Any]:
    request = DelegationRequest.model_validate(kwargs)
    return runtime.delegate(request).model_dump()
