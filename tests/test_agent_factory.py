from __future__ import annotations

from pathlib import Path

from agent_core.config import RuntimeConfig
from agent_core.context import AgentRuntimeContext
from agent_core.factory import create_write_agent


class FakeCheckpointer:
    pass


def test_agent_factory_builds_deep_agent_with_tools_middleware_and_context(tmp_path):
    captured = {}

    def fake_create_deep_agent(**kwargs):
        captured.update(kwargs)
        return {"agent": "fake"}

    cfg = RuntimeConfig(
        repo_root=Path.cwd(),
        workspace_root=tmp_path / "workspace",
        project_root=tmp_path / "workspace" / "project",
    )
    agent = create_write_agent(cfg, deep_agent_factory=fake_create_deep_agent, checkpointer=FakeCheckpointer(), model="fake-model")

    assert agent == {"agent": "fake"}
    assert captured["model"] == "fake-model"
    assert captured["context_schema"] is AgentRuntimeContext
    assert captured["backend"].cwd == Path.cwd().resolve()
    assert captured["backend"].virtual_mode is True
    assert captured["permissions"][0].mode == "deny"
    assert "/.env" in captured["permissions"][0].paths
    assert captured["permissions"][-1].mode == "deny"
    assert captured["permissions"][-1].paths == ["/**"]
    assert captured["memory"] == [str(Path.cwd() / "skill_packs" / "academic-paper-writing" / "references" / "README.md")]
    assert {subagent["name"] for subagent in captured["subagents"]} == {
        "requirement-analysis-agent",
        "literature-review-agent",
        "literature-paper-reader-agent",
        "paper-outline-agent",
        "content-generation-agent",
        "content-section-writer-agent",
        "academic-formatting-agent",
        "polish-plagiarism-agent",
    }
    assert {tool.name for tool in captured["tools"]} == {
        "ask_user",
        "execute_bash",
        "update_artifact_manifest",
        "update_progress",
        "inspect_progress",
        "delegate_to_agent",
        "search_knowledge",
        "extract_sources",
    }
    assert {mw.name for mw in captured["middleware"]} == {
        "writeagent_workflow_gate", "writeagent_trace", "writeagent_guardrails"
    }
    assert captured["interrupt_on"]["ask_user"]["allowed_decisions"] == ["respond"]
    assert captured["interrupt_on"]["execute_bash"] is False
    assert captured["interrupt_on"]["search_knowledge"] is False
    assert captured["interrupt_on"]["extract_sources"] is False
