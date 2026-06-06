from __future__ import annotations

from delegation.capability_index import CapabilityIndex
from delegation.registry import AgentRegistration, AgentRegistry
from delegation.router import DelegationRouter
from delegation.runtime import DelegationRuntime
from delegation.schema import DelegationRequest, DelegationResult


def test_delegation_registry_router_runtime_and_remote_mock():
    registry = AgentRegistry()
    registry.register(AgentRegistration(
        agent_id="local-outline",
        capabilities=["outline"],
        backend="local",
        handle=lambda request: DelegationResult(status="ok", summary=f"handled {request.capability}"),
    ))
    registry.register(AgentRegistration(
        agent_id="remote-outline",
        capabilities=["outline"],
        backend="remote_a2a",
        handle=lambda payload: {"status": "ok", "summary": "remote handled", "output_artifacts": [], "messages": []},
    ))

    index = CapabilityIndex(registry)
    assert [agent.agent_id for agent in index.candidates("outline")] == ["local-outline", "remote-outline"]
    router = DelegationRouter(registry, index)
    assert router.route(DelegationRequest(capability="outline", instruction="x")).agent_id == "local-outline"
    result = DelegationRuntime(registry, router).delegate(DelegationRequest(capability="outline", instruction="x"))
    assert result.status == "ok"
    assert "outline" in result.summary

    remote = DelegationRuntime(registry, router).delegate(DelegationRequest(receiver_agent_id="remote-outline", capability="outline", instruction="x"))
    assert remote.summary == "remote handled"
