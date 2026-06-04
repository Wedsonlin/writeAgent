from __future__ import annotations

import json
from pathlib import Path

from agent.a2a.types import SubAgentSpec
from agent.llm_gateway import LLMGateway
from agent.react.subagent_graph import SubAgentNodes
from agent.react.subagent_tools import create_subagent_tools
from agent.state_store import StateStore
from agent.subagents.runtime import SubAgentRuntime
from agent.trace_store import TraceStore


def test_subagent_runtime_writes_intermediate_and_trace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    state_path = workspace / "state.json"
    state_path.write_text(json.dumps({"user_request": "写一篇 CFRP 损伤检测论文"}), encoding="utf-8")
    trace_store = TraceStore(workspace)
    runtime = SubAgentRuntime(
        llm_gateway=LLMGateway(trace_store=trace_store),
        state_store=StateStore(),
        trace_store=trace_store,
    )
    spec = SubAgentSpec(
        subagent_id="sa_001",
        parent_agent_id="main",
        role="requirement analysis specialist",
        task="Create a writing task.",
        input_keys=["user_request"],
        output_key="intermediate.requirement.raw_writing_task",
        skill_context=["writing-requirement-analysis"],
        prompt_refs=["skills/writing-requirement-analysis/prompts/extract_writing_task.md"],
        output_schema="WritingTask",
        allowed_tools=["inspect_state", "read_state_keys"],
    )

    result = runtime.run(spec, state_path)

    assert result.status == "completed"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["intermediate"]["requirement"]["raw_writing_task"]["topic"]
    assert trace_store.subagent_trace_path.exists()
    assert trace_store.llm_trace_path.exists()


def test_subagent_runtime_rejects_unauthorized_tool(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"user_request": "x"}), encoding="utf-8")
    runtime = SubAgentRuntime(
        llm_gateway=LLMGateway(),
        state_store=StateStore(),
        trace_store=TraceStore(tmp_path),
    )
    spec = SubAgentSpec(
        subagent_id="sa_001",
        parent_agent_id="main",
        role="writer",
        task="Run a skill.",
        input_keys=["user_request"],
        output_key="intermediate.x",
        output_schema={"type": "object"},
        allowed_tools=["run_skill"],
    )

    result = runtime.run(spec, state_path)

    assert result.status == "failed"
    assert any(error["detail"].get("tool") == "run_skill" for error in result.errors)


def test_subagent_runtime_rejects_unauthorized_write(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"user_request": "x"}), encoding="utf-8")
    runtime = SubAgentRuntime(
        llm_gateway=LLMGateway(),
        state_store=StateStore(),
        trace_store=TraceStore(tmp_path),
    )
    spec = SubAgentSpec(
        subagent_id="sa_001",
        parent_agent_id="main",
        role="writer",
        task="Write formal output.",
        input_keys=["user_request"],
        output_key="draft",
        output_schema={"type": "object"},
    )

    result = runtime.run(spec, state_path)

    assert result.status == "failed"
    assert result.errors


def test_subagent_file_tool_requires_authorized_ref(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    outputs = workspace / "outputs"
    outputs.mkdir(parents=True)
    state_path = workspace / "state.json"
    state_path.write_text(json.dumps({"outline": {"title": "x"}}), encoding="utf-8")
    (outputs / "outline.md").write_text("authorized outline", encoding="utf-8")
    (outputs / "other.md").write_text("not authorized", encoding="utf-8")
    spec = SubAgentSpec(
        subagent_id="sa_001",
        parent_agent_id="main",
        role="reviewer",
        task="Read an authorized file.",
        input_keys=["outline"],
        output_key="intermediate.review",
        output_schema={"type": "object"},
        file_refs=["outputs/outline.md"],
    )
    tools = {
        tool.name: tool
        for tool in create_subagent_tools(
            spec=spec,
            state_path=state_path,
            state_store=StateStore(),
            result_sink={},
        )
    }

    allowed = json.loads(tools["read_workspace_file"].invoke({"path": "outputs/outline.md"}))
    denied = json.loads(tools["read_workspace_file"].invoke({"path": "outputs/other.md"}))

    assert allowed["status"] == "ok"
    assert allowed["content"] == "authorized outline"
    assert denied["status"] == "fatal"


def test_subagent_write_intermediate_bare_list_gets_schema_hint(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"writing_task": {"topic": "x"}}), encoding="utf-8")
    spec = SubAgentSpec(
        subagent_id="sa_001",
        parent_agent_id="main",
        role="writer",
        task="Write claims.",
        input_keys=["writing_task"],
        output_key="intermediate.claims",
        output_schema={"type": "object", "required": ["papers"]},
    )
    tools = create_subagent_tools(
        spec=spec,
        state_path=state_path,
        state_store=StateStore(),
        result_sink={},
    )
    nodes = SubAgentNodes(model=FakeModel(), tools=tools, result_sink={})

    observation = json.loads(nodes._invoke_tool("write_intermediate", {"value": [{"id": "paper-1"}]}))

    assert observation["status"] == "fatal"
    assert "wrap arrays" in observation["error"]


class FakeModel:
    def bind_tools(self, tools):  # type: ignore[no-untyped-def]
        return self
