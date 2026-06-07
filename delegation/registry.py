"""Agent registry for delegation backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class AgentRegistration:
    agent_id: str
    capabilities: list[str]
    backend: Literal["local", "remote_a2a"] = "local"
    handle: Any = None # agent callable function
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, AgentRegistration] = {}

    def register(self, registration: AgentRegistration) -> None:
        self._agents[registration.agent_id] = registration

    def get(self, agent_id: str) -> AgentRegistration | None:
        return self._agents.get(agent_id)

    def all(self) -> list[AgentRegistration]:
        return list(self._agents.values())
