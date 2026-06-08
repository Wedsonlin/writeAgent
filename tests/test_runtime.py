from __future__ import annotations

from langgraph.types import Command

from agent_core.context import AgentRuntimeContext
from agent_core.runtime import WriteAgentRuntime


class FakeAgent:
    def __init__(self) -> None:
        self.calls = []

    def invoke(self, payload, **kwargs):
        self.calls.append((payload, kwargs))
        return {"ok": True}


def _context() -> AgentRuntimeContext:
    return AgentRuntimeContext(
        user_id="user",
        workspace_id="workspace",
        project_id="project",
        skill_pack_id="academic-paper-writing",
        artifact_root="artifacts",
    )


def test_runtime_context_has_frontend_defaults():
    context = AgentRuntimeContext()

    assert context.user_id == "frontend-user"
    assert context.workspace_id == "local"
    assert context.project_id == "default"
    assert context.skill_pack_id == "academic-paper-writing"
    assert context.artifact_root == ".writeagent/projects/default/artifacts"


def test_runtime_invoke_uses_thread_id_and_v2_interrupt_output():
    agent = FakeAgent()
    runtime = WriteAgentRuntime(agent=agent)

    result = runtime.invoke("hello", _context(), thread_id="thread-1")

    payload, kwargs = agent.calls[0]
    assert result == {"ok": True}
    assert payload == {"messages": [{"role": "user", "content": "hello"}]}
    assert kwargs["config"] == {"configurable": {"thread_id": "thread-1"}}
    assert kwargs["version"] == "v2"


def test_runtime_resume_uses_command_resume_on_same_thread():
    agent = FakeAgent()
    runtime = WriteAgentRuntime(agent=agent)

    result = runtime.resume({"decisions": [{"type": "respond", "message": "topic is AI"}]}, _context(), thread_id="thread-1")

    payload, kwargs = agent.calls[0]
    assert result == {"ok": True}
    assert isinstance(payload, Command)
    assert payload.resume == {"decisions": [{"type": "respond", "message": "topic is AI"}]}
    assert kwargs["config"] == {"configurable": {"thread_id": "thread-1"}}
    assert kwargs["version"] == "v2"
