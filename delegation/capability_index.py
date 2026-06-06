"""Capability index for registered agents."""

from __future__ import annotations

from .registry import AgentRegistration, AgentRegistry


class CapabilityIndex:
    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry

    def candidates(self, capability: str) -> list[AgentRegistration]:
        return [agent for agent in self.registry.all() if capability in agent.capabilities]
