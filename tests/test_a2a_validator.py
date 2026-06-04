from __future__ import annotations

from pathlib import Path

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


def test_subagent_spec_accepts_authorized_file_ref(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    outputs = workspace / "outputs"
    outputs.mkdir(parents=True)
    (outputs / "outline.md").write_text("outline", encoding="utf-8")
    spec = SubAgentSpec(
        subagent_id="sa_001",
        parent_agent_id="main",
        role="reviewer",
        task="Review a generated outline.",
        input_keys=["outline"],
        output_key="intermediate.review",
        output_schema={"type": "object"},
        allowed_tools=["read_workspace_file"],
        file_refs=["outputs/outline.md"],
    )

    assert validate_subagent_spec(spec, file_workspace_root=workspace) == []


def test_subagent_spec_rejects_unsafe_file_ref(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("secret", encoding="utf-8")
    spec = SubAgentSpec(
        subagent_id="sa_001",
        parent_agent_id="main",
        role="reviewer",
        task="Review a file.",
        input_keys=["outline"],
        output_key="intermediate.review",
        output_schema={"type": "object"},
        allowed_tools=["read_workspace_file"],
        file_refs=[str(outside), "../outside.md"],
    )

    errors = validate_subagent_spec(spec, file_workspace_root=workspace)

    assert any(error.detail.get("file_ref") == str(outside) for error in errors)
    assert any(error.detail.get("file_ref") == "../outside.md" for error in errors)
