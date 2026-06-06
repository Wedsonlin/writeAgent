"""Delegation routing policy."""

from __future__ import annotations

from .capability_index import CapabilityIndex
from .registry import AgentRegistration, AgentRegistry
from .schema import DelegationRequest


class DelegationRouter:
    def __init__(self, registry: AgentRegistry, capability_index: CapabilityIndex | None = None) -> None:
        self.registry = registry
        self.capability_index = capability_index or CapabilityIndex(registry)

    def route(self, request: DelegationRequest) -> AgentRegistration | None:
        if request.receiver_agent_id:
            return self.registry.get(request.receiver_agent_id)
        candidates = self.capability_index.candidates(request.capability)
        local = [candidate for candidate in candidates if candidate.backend == "local"]
        return (local or candidates or [None])[0]
