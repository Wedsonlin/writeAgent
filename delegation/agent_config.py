"""Declarative agent discovery configuration."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class SubAgentConfig(BaseModel):
    """Configuration for a local Deep Agents subagent."""

    name: str
    description: str
    prompt_file: str
    skills: list[str] = Field(default_factory=list)
    model: str | None = None


class AgentConfig(BaseModel):
    """Single discovered agent entry."""

    id: str
    routing: Literal["subagent", "delegation"]
    capability: str
    stage_id: str | None = None
    backend: Literal["local", "remote_a2a"] | None = None
    endpoint: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    subagent: SubAgentConfig | None = None

    @model_validator(mode="after")
    def validate_routing_fields(self) -> "AgentConfig":
        if self.routing == "subagent":
            if self.subagent is None:
                raise ValueError("subagent routing requires a subagent block")
            if self.backend is not None:
                raise ValueError("subagent routing must not set backend")
            return self

        if self.backend is None:
            raise ValueError("delegation routing requires backend")
        if self.subagent is not None:
            raise ValueError("delegation routing must not set a subagent block")
        return self


class AgentsConfig(BaseModel):
    """Top-level agents.yaml schema."""

    version: int = 1
    disable_general_purpose: bool = False
    agents: list[AgentConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "AgentsConfig":
        ids = [agent.id for agent in self.agents]
        if len(ids) != len(set(ids)):
            raise ValueError("agent ids must be unique")
        return self
