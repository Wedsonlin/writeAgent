from __future__ import annotations

from agent.a2a.types import SubAgentSpec
from agent.a2a.validator import validate_subagent_spec


def test_subagent_spec_accepts_intermediate_write() -> None:
    spec = SubAgentSpec(
        subagent_id="sa_001",
        parent_agent_id="main",
        role="requirement analyst",
        task="Extract a writing task.",
        input_keys=["user_request"],
        output_key="intermediate.requirement.raw_writing_task",
        output_schema="WritingTask",
        allowed_tools=["inspect_state", "read_state_keys"],
    )

    assert validate_subagent_spec(spec) == []


def test_subagent_spec_rejects_formal_output_write() -> None:
    spec = SubAgentSpec(
        subagent_id="sa_001",
        parent_agent_id="main",
        role="writer",
        task="Write formal output.",
        input_keys=["user_request"],
        output_key="writing_task",
        output_schema="WritingTask",
    )

    errors = validate_subagent_spec(spec)

    assert any(error.code == "policy_violation" for error in errors)


def test_subagent_spec_rejects_forbidden_tool() -> None:
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

    errors = validate_subagent_spec(spec)

    assert any(error.detail.get("tool") == "run_skill" for error in errors)
