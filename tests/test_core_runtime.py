from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from langchain.agents.middleware.types import ModelResponse
from langchain_core.messages import AIMessage
from langgraph.errors import GraphBubbleUp

from agent_core.config import ModelConfig, RuntimeConfig, sanitize_project_id
from agent_core.context import AgentRuntimeContext
from agent_core.factory import (
    _ensure_project_state_async,
    _project_config_from_runtime,
    create_write_agent,
)
import agent_core.factory as factory_module
from artifacts.manifest import ArtifactManifest
from artifacts.schemas import ArtifactMeta
from delegation.discovery import AgentDiscovery
from middleware.guardrails import check_command
from middleware.trace import TraceMiddleware
from project_store.ledger import ProgressLedger
from server import webapp
from traces.store import TraceStore
from workflows.loader import load_workflow


class FakeCheckpointer:
    pass


def test_runtime_config_model_and_project_layout(monkeypatch, tmp_path):
    monkeypatch.setenv("WRITEAGENT_LLM_API_KEY", "test-key")
    monkeypatch.setenv("WRITEAGENT_LLM_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("WRITEAGENT_MODEL", "openai:qwen-plus")
    monkeypatch.setenv("WRITEAGENT_DISABLE_MODEL_STREAMING", "true")

    model_config = ModelConfig.from_env()
    assert getattr(model_config.model, "model_name") == "qwen-plus"
    assert str(getattr(model_config.model, "openai_api_base")) == "https://example.test/v1"
    assert getattr(model_config.model, "disable_streaming") is True

    base = RuntimeConfig(repo_root=tmp_path, workspace_root=tmp_path / ".writeagent")
    cfg = base.for_project("20260626-143012_thread-abc")
    assert cfg.project_root == tmp_path / ".writeagent" / "projects" / "20260626-143012_thread-abc"
    assert cfg.artifact_root == cfg.project_root / "artifacts"
    assert cfg.tmp_root == cfg.project_root / "tmp"
    assert cfg.stage_artifact_path("requirement_analysis").name == "01-论文写作任务书.json"
    assert cfg.stage_artifact_path("polish_and_plagiarism", ".pdf").name == "06-润色论文终稿.pdf"

    sanitized = base.for_project("../bad/thread:x")
    assert sanitized.project_id == "bad-thread-x"
    assert sanitize_project_id("   ") == "default"
    assert base.workspace_root.resolve() in sanitized.project_root.resolve().parents


def test_agent_factory_registers_core_tools_and_project_context(tmp_path):
    calls = []

    def fake_create_deep_agent(**kwargs):
        calls.append(kwargs)
        return {"agent": kwargs["name"], "subagents": kwargs.get("subagents", [])}

    cfg = RuntimeConfig(repo_root=Path.cwd(), workspace_root=tmp_path / ".writeagent")
    agent = create_write_agent(
        cfg,
        deep_agent_factory=fake_create_deep_agent,
        checkpointer=FakeCheckpointer(),
        model="fake-model",
    )

    captured = calls[-1]
    calls_by_name = {call["name"]: call for call in calls}

    assert agent["agent"] == "writeAgent"
    assert captured["context_schema"] is AgentRuntimeContext
    assert {tool.name for tool in captured["tools"]} == {
        "ask_user",
        "execute_bash",
        "update_artifact_manifest",
        "update_progress",
        "inspect_progress",
        "search_knowledge",
        "extract_sources",
    }
    assert {mw.name for mw in captured["middleware"]} == {
        "writeagent_workflow_gate",
        "writeagent_trace",
        "writeagent_guardrails",
    }
    assert captured["interrupt_on"]["ask_user"]["allowed_decisions"] == ["respond"]
    assert captured["interrupt_on"]["execute_bash"] is False
    assert captured["subagents"]
    root_subagent_names = {subagent["name"] for subagent in captured["subagents"]}
    assert "literature-paper-reader-agent" not in root_subagent_names
    assert "content-section-writer-agent" not in root_subagent_names
    assert "literature-review-agent" in root_subagent_names
    assert "content-generation-agent" in root_subagent_names

    assert {
        subagent["name"]
        for subagent in calls_by_name["literature-review-agent"]["subagents"]
    } == {"literature-paper-reader-agent"}
    assert {
        subagent["name"]
        for subagent in calls_by_name["content-generation-agent"]["subagents"]
    } == {"content-section-writer-agent"}

    for subagent in captured["subagents"]:
        if "middleware" not in subagent:
            continue
        middleware_names = {mw.name for mw in subagent["middleware"]}
        assert {
            "writeagent_workflow_gate",
            "writeagent_trace",
            "writeagent_guardrails",
        }.issubset(middleware_names)
    assert [p.paths for p in captured["permissions"] if p.mode == "allow"][0] == [
        "/.writeagent/projects",
        "/.writeagent/projects/**",
    ]
    for tool in captured["tools"]:
        schema_model = tool.args_schema or tool.get_input_schema()
        assert "runtime" not in schema_model.model_json_schema().get("properties", {})


def test_agent_discovery_rejects_unknown_child_subagent(tmp_path):
    config_path = tmp_path / "agents.yaml"
    config_path.write_text(
        """
version: 1
agents:
  - id: parent
    routing: subagent
    capability: parent
    subagent:
      name: parent-agent
      description: Parent
      prompt_file: prompt.md
      children:
        - missing-agent
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown child subagent missing-agent"):
        AgentDiscovery.load(config_path, skill_pack_root=tmp_path, repo_root=tmp_path)


def test_agent_discovery_rejects_self_child_subagent(tmp_path):
    config_path = tmp_path / "agents.yaml"
    config_path.write_text(
        """
version: 1
agents:
  - id: parent
    routing: subagent
    capability: parent
    subagent:
      name: parent-agent
      description: Parent
      prompt_file: prompt.md
      children:
        - parent-agent
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="cannot list itself as a child"):
        AgentDiscovery.load(config_path, skill_pack_root=tmp_path, repo_root=tmp_path)


def test_agent_discovery_rejects_child_cycles(tmp_path):
    config_path = tmp_path / "agents.yaml"
    config_path.write_text(
        """
version: 1
agents:
  - id: parent
    routing: subagent
    capability: parent
    subagent:
      name: parent-agent
      description: Parent
      prompt_file: prompt.md
      children:
        - child-agent
  - id: child
    routing: subagent
    capability: child
    subagent:
      name: child-agent
      description: Child
      prompt_file: prompt.md
      children:
        - parent-agent
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="cycle"):
        AgentDiscovery.load(config_path, skill_pack_root=tmp_path, repo_root=tmp_path)


def test_ensure_project_state_async_runs_outside_event_loop(monkeypatch, tmp_path):
    calls: list[str] = []

    def record(label: str) -> None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            calls.append(label)
            return
        raise AssertionError(f"{label} ran in the event loop thread")

    monkeypatch.setattr(
        factory_module,
        "_ensure_project_state",
        lambda project_cfg, workflow: record("ensure_project_state"),
    )

    cfg = RuntimeConfig(repo_root=Path.cwd(), workspace_root=tmp_path / ".writeagent")
    workflow = load_workflow(cfg.skill_pack_root / "workflow.yaml")

    asyncio.run(_ensure_project_state_async(cfg.for_project("threaded-project"), workflow))

    assert calls == ["ensure_project_state"]


def test_tool_runtime_project_context_survives_threaded_execution(tmp_path):
    cfg = RuntimeConfig(repo_root=Path.cwd(), workspace_root=tmp_path / ".writeagent")
    trace = TraceMiddleware(TraceStore(tmp_path / "trace.jsonl"), runtime_config=cfg)
    request = SimpleNamespace(
        runtime=SimpleNamespace(context=AgentRuntimeContext(project_id="20260626-143012_thread-xyz")),
        tool_call={"name": "update_progress", "args": {}, "id": "call-test"},
    )

    async def run_tool():
        async def handler(_request):
            return await asyncio.to_thread(lambda: _project_config_from_runtime(cfg, None).project_id)

        return await trace.awrap_tool_call(request, handler)

    assert asyncio.run(run_tool()) == "20260626-143012_thread-xyz"


def test_trace_middleware_records_interrupted_subagent_tool_call(tmp_path):
    cfg = RuntimeConfig(repo_root=Path.cwd(), workspace_root=tmp_path / ".writeagent")
    trace = TraceMiddleware(
        TraceStore(tmp_path / "fallback.jsonl"),
        runtime_config=cfg,
        agent_scope="subagent",
        agent_name="requirement-analysis-agent",
    )
    request = SimpleNamespace(
        runtime=SimpleNamespace(context=AgentRuntimeContext(project_id="20260626-143012_thread-hitl")),
        tool_call={
            "name": "ask_user",
            "args": {"question": "请选择目标期刊"},
            "id": "call-hitl",
        },
    )

    def interrupted(_request):
        raise GraphBubbleUp()

    try:
        trace.wrap_tool_call(request, interrupted)
    except GraphBubbleUp:
        pass
    else:  # pragma: no cover - defensive assertion for this test
        raise AssertionError("GraphBubbleUp should propagate")

    events = TraceStore(cfg.for_project("20260626-143012_thread-hitl").trace_path).read_all()
    assert len(events) == 1
    assert events[0].event_type == "tool_call"
    assert events[0].status == "interrupted"
    assert events[0].payload["tool"] == "ask_user"
    assert events[0].payload["agent_scope"] == "subagent"
    assert events[0].payload["agent_name"] == "requirement-analysis-agent"
    assert events[0].payload["error_type"] == "GraphBubbleUp"


def test_trace_middleware_records_model_call_without_message_content(tmp_path):
    cfg = RuntimeConfig(repo_root=Path.cwd(), workspace_root=tmp_path / ".writeagent")
    trace = TraceMiddleware(
        TraceStore(tmp_path / "fallback.jsonl"),
        runtime_config=cfg,
        agent_scope="subagent",
        agent_name="requirement-analysis-agent",
    )
    request = SimpleNamespace(
        runtime=SimpleNamespace(context=AgentRuntimeContext(project_id="20260626-143012_thread-model")),
        model="fake-model",
        messages=[{"role": "human", "content": "secret draft content"}],
    )

    def handler(_request):
        return ModelResponse(
            result=[
                AIMessage(
                    content="do not record this model response",
                    tool_calls=[{"name": "ask_user", "args": {"question": "目标期刊"}, "id": "call-model"}],
                )
            ]
        )

    response = trace.wrap_model_call(request, handler)

    assert response.result[0].tool_calls[0]["name"] == "ask_user"
    events = TraceStore(cfg.for_project("20260626-143012_thread-model").trace_path).read_all()
    assert len(events) == 1
    assert events[0].event_type == "model_call"
    assert events[0].status == "success"
    assert events[0].payload["agent_scope"] == "subagent"
    assert events[0].payload["agent_name"] == "requirement-analysis-agent"
    assert events[0].payload["message_count"] == 1
    assert events[0].payload["tool_calls"] == ["ask_user"]
    assert "secret draft content" not in events[0].model_dump_json()
    assert "do not record this model response" not in events[0].model_dump_json()


def test_execute_bash_guardrail_allows_only_current_project_tmp_helpers():
    assert check_command("python .writeagent/projects/20260626-143012_thread-abc/tmp/build_stage4_input.py").allowed
    assert not check_command("python scripts/random.py").allowed


def test_project_scoped_progress_and_artifact_routes(monkeypatch, tmp_path):
    base_cfg = RuntimeConfig(repo_root=Path.cwd(), workspace_root=tmp_path / ".writeagent")
    monkeypatch.setattr(webapp, "_config", lambda: base_cfg)
    cfg = base_cfg.for_project("20260626-143012_thread-abc")
    cfg.ensure_dirs()

    workflow = load_workflow(cfg.skill_pack_root / "workflow.yaml")
    ledger = ProgressLedger.create(workflow.id, workflow.stage_ids)
    ledger.update_stage("academic_formatting", "completed", output_artifacts=["formatted-1"])
    ledger.save(cfg.progress_path)

    artifact_json = cfg.stage_artifact_path("academic_formatting")
    markdown = cfg.stage_artifact_path("academic_formatting", ".md")
    docx = cfg.stage_artifact_path("academic_formatting", ".docx")
    artifact_json.write_text(
        json.dumps(
            {
                "artifact_type": "formatted_draft",
                "formatted_draft": {
                    "markdown_path": str(markdown),
                    "docx_path": str(docx),
                    "pdf_path": None,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    markdown.write_text("# formatted\n", encoding="utf-8")
    docx.write_bytes(b"PK\x03\x04fake-docx")

    manifest = ArtifactManifest.load(cfg.manifest_path)
    manifest.upsert(
        ArtifactMeta(
            artifact_id="formatted-1",
            artifact_type="formatted_draft",
            path=str(artifact_json),
            stage_id="academic_formatting",
        )
    )

    client = TestClient(webapp.app)
    query = "?project_id=20260626-143012_thread-abc"

    progress = client.get(f"/api/workflow/progress{query}")
    assert progress.status_code == 200
    assert progress.json()["project_id"] == "20260626-143012_thread-abc"
    assert progress.json()["artifacts"][0]["artifact_id"] == "formatted-1"

    assert client.get(f"/api/artifacts/formatted-1/files/json{query}").status_code == 200
    assert client.get(f"/api/artifacts/formatted-1/files/markdown{query}").text.replace("\r\n", "\n") == "# formatted\n"
    assert client.get(f"/api/artifacts/formatted-1/files/docx{query}").content.startswith(b"PK")
    assert client.get("/api/artifacts/%2E%2E/files/json").status_code == 404
