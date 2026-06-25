from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from agent_core.config import RuntimeConfig
from artifacts.manifest import ArtifactManifest
from artifacts.schemas import ArtifactMeta
from project_store.ledger import ProgressLedger
from server import webapp
from workflows.loader import load_workflow


def test_health_route():
    client = TestClient(webapp.app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "writeAgent"}


def test_workflow_meta_route(monkeypatch, tmp_path):
    _patch_config(monkeypatch, tmp_path)
    client = TestClient(webapp.app)

    response = client.get("/api/workflow/meta")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_id"] == "academic-paper-writing-workflow"
    assert [stage["id"] for stage in payload["stages"]] == [
        "requirement_analysis",
        "literature_review",
        "paper_outline",
        "content_generation",
        "academic_formatting",
        "polish_and_plagiarism",
    ]
    assert payload["stages"][0]["produces"] == ["writing_task"]


def test_workflow_progress_route_reads_ledger_and_manifest(monkeypatch, tmp_path):
    cfg = _patch_config(monkeypatch, tmp_path)
    workflow = load_workflow(cfg.skill_pack_root / "workflow.yaml")
    ledger = ProgressLedger.create(workflow.id, workflow.stage_ids)
    ledger.update_stage("requirement_analysis", "completed", output_artifacts=["writing-task-1"])
    ledger.save(cfg.progress_path)
    manifest = ArtifactManifest.load(cfg.manifest_path)
    manifest.upsert(
        ArtifactMeta(
            artifact_id="writing-task-1",
            artifact_type="writing_task",
            path="artifacts/writing_task.json",
            stage_id="requirement_analysis",
        )
    )
    client = TestClient(webapp.app)

    response = client.get("/api/workflow/progress")

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_stage"] == "literature_review"
    assert payload["stages"][0]["stage_id"] == "requirement_analysis"
    assert payload["stages"][0]["status"] == "completed"
    assert payload["artifacts"][0]["artifact_id"] == "writing-task-1"


def test_artifact_file_route_serves_registered_sidecars_only(monkeypatch, tmp_path):
    cfg = _patch_config(monkeypatch, tmp_path)
    artifact_json = cfg.artifact_root / "formatted.json"
    markdown = cfg.artifact_root / "formatted.md"
    docx = cfg.artifact_root / "formatted.docx"
    artifact_json.write_text(
        (
            '{"artifact_type":"formatted_draft","formatted_draft":'
            '{"markdown_path":"'
            + str(markdown).replace("\\", "\\\\")
            + '","docx_path":"'
            + str(docx).replace("\\", "\\\\")
            + '","pdf_path":null}}'
        ),
        encoding="utf-8",
    )
    markdown.write_text("# 格式化稿\n", encoding="utf-8")
    docx.write_bytes(b"PK\x03\x04fake-docx")
    manifest = ArtifactManifest.load(cfg.manifest_path)
    manifest.upsert(
        ArtifactMeta(
            artifact_id="formatted-1",
            artifact_type="formatted_draft",
            path=str(artifact_json),
            stage_id="academic_formatting",
            metadata={"markdown_path": str(markdown)},
        )
    )
    client = TestClient(webapp.app)

    json_response = client.get("/api/artifacts/formatted-1/files/json")
    markdown_response = client.get("/api/artifacts/formatted-1/files/markdown")
    docx_response = client.get("/api/artifacts/formatted-1/files/docx")
    pdf_response = client.get("/api/artifacts/formatted-1/files/pdf")
    unknown_response = client.get("/api/artifacts/missing/files/json")
    traversal_response = client.get("/api/artifacts/%2E%2E/files/json")

    assert json_response.status_code == 200
    assert json_response.json()["artifact_type"] == "formatted_draft"
    assert markdown_response.status_code == 200
    assert "格式化稿" in markdown_response.text
    assert docx_response.status_code == 200
    assert docx_response.content.startswith(b"PK")
    assert pdf_response.status_code == 404
    assert unknown_response.status_code == 404
    assert traversal_response.status_code == 404


def test_case_original_requirement_route_returns_fixed_case_file(monkeypatch, tmp_path):
    _patch_config(monkeypatch, tmp_path)
    client = TestClient(webapp.app)

    response = client.get("/api/case/original-requirement")

    assert response.status_code == 200
    payload = response.json()
    assert payload["path"].endswith("case/00-用户原始需求.md")
    assert "AI Infrastructure" in payload["content"]
    assert "seed.bib" in payload["content"]
    assert "软件学报排版样例2025年版.doc" in payload["content"]


def _patch_config(monkeypatch, tmp_path: Path) -> RuntimeConfig:
    cfg = RuntimeConfig(
        repo_root=Path.cwd(),
        workspace_root=tmp_path / ".writeagent",
        project_root=tmp_path / ".writeagent" / "projects" / "default",
    )
    cfg.ensure_dirs()
    monkeypatch.setattr(webapp, "_config", lambda: cfg)
    return cfg
