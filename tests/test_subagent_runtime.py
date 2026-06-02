from __future__ import annotations

import json
from pathlib import Path

from agent.a2a.types import SubAgentSpec
from agent.llm_gateway import LLMGateway
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
