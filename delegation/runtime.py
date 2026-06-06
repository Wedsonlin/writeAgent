"""Delegation runtime facade."""

from __future__ import annotations

from traces.store import TraceStore
from .adapters.local import LocalDelegationAdapter
from .adapters.remote_a2a import RemoteA2AAdapter
from .registry import AgentRegistry
from .router import DelegationRouter
from .schema import DelegationRequest, DelegationResult


class DelegationRuntime:
    def __init__(
        self,
        registry: AgentRegistry,
        router: DelegationRouter | None = None,
        adapters: dict[str, object] | None = None,
        trace_store: TraceStore | None = None,
    ) -> None:
        self.registry = registry
        self.router = router or DelegationRouter(registry)
        self.adapters = adapters or {"local": LocalDelegationAdapter(), "remote_a2a": RemoteA2AAdapter()}
        self.trace_store = trace_store

    def delegate(self, request: DelegationRequest) -> DelegationResult:
        registration = self.router.route(request)
        if registration is None:
            result = DelegationResult(status="blocked", summary=f"No agent can satisfy capability: {request.capability}")
        else:
            adapter = self.adapters.get(registration.backend)
            if adapter is None:
                result = DelegationResult(status="failed", summary=f"No adapter for backend: {registration.backend}")
            else:
                result = adapter.invoke(registration.handle, request)  # type: ignore[attr-defined]
        if self.trace_store is not None:
            self.trace_store.append("delegation", status=result.status, payload={"request": request.model_dump(), "result": result.model_dump()})
        return result
