"""Custom HTTP routes mounted beside the LangGraph API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from agent_core.config import RuntimeConfig
from artifacts.schemas import ArtifactMeta
from artifacts.manifest import ArtifactManifest
from project_store.ledger import ProgressLedger
from workflows.loader import load_workflow


app = FastAPI(title="writeAgent frontend support")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "writeAgent"}


@app.get("/api/workflow/meta")
def workflow_meta() -> dict[str, Any]:
    cfg = _config()
    workflow = load_workflow(cfg.skill_pack_root / "workflow.yaml")
    return {
        "workflow_id": workflow.id,
        "title": workflow.title,
        "stages": [
            {
                "id": stage.id,
                "title": stage.title,
                "skill": stage.skill,
                "requires": stage.requires,
                "produces": stage.produces,
                "description": stage.description,
                "quality_checks": stage.quality_checks,
            }
            for stage in workflow.stages
        ],
    }


@app.get("/api/workflow/progress")
def workflow_progress() -> dict[str, Any]:
    cfg = _config()
    cfg.ensure_dirs()
    workflow = load_workflow(cfg.skill_pack_root / "workflow.yaml")
    if not cfg.progress_path.exists():
        ProgressLedger.create(workflow.id, workflow.stage_ids).save(cfg.progress_path)

    ledger = ProgressLedger.load(cfg.progress_path)
    manifest = ArtifactManifest.load(cfg.manifest_path)
    return {
        "workflow_id": ledger.workflow_id,
        "current_stage": ledger.current_stage,
        "blocked_reason": ledger.blocked_reason,
        "updated_at": ledger.updated_at,
        "stages": [stage.model_dump() for stage in ledger.stages.values()],
        "artifacts": [meta.model_dump() for meta in manifest.artifacts.values()],
    }


@app.get("/api/case/original-requirement")
def case_original_requirement() -> dict[str, str]:
    cfg = _config()
    target = (cfg.repo_root / "case" / "00-用户原始需求.md").resolve()
    if not target.exists() or not _is_allowed_path(cfg, target):
        raise HTTPException(status_code=404, detail="Case requirement not found")
    return {
        "path": "case/00-用户原始需求.md",
        "content": target.read_text(encoding="utf-8"),
    }


@app.get("/api/artifacts/{artifact_id}/files/{kind}")
def artifact_file(artifact_id: str, kind: str) -> FileResponse:
    if kind not in {"json", "markdown", "docx", "pdf"} or _looks_unsafe_segment(artifact_id):
        raise HTTPException(status_code=404, detail="Artifact file not found")

    cfg = _config()
    manifest = ArtifactManifest.load(cfg.manifest_path)
    meta = manifest.get(artifact_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Artifact file not found")

    target = _artifact_file_path(cfg, meta, kind)
    if target is None or not target.exists() or not _is_allowed_path(cfg, target):
        raise HTTPException(status_code=404, detail="Artifact file not found")
    return FileResponse(target, filename=target.name)


def _config() -> RuntimeConfig:
    return RuntimeConfig()


def _artifact_file_path(cfg: RuntimeConfig, meta: ArtifactMeta, kind: str) -> Path | None:
    artifact_path = _resolve_known_path(cfg, meta.path)
    if kind == "json":
        return artifact_path
    if artifact_path is None or not artifact_path.exists() or not _is_allowed_path(cfg, artifact_path):
        return None

    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}

    artifact_body = _artifact_body(payload, meta.artifact_type)
    raw_path = _path_from_payload_or_metadata(artifact_body, meta.metadata, kind)
    return _resolve_known_path(cfg, raw_path) if raw_path else None


def _artifact_body(payload: dict[str, Any], artifact_type: str) -> dict[str, Any]:
    body = payload.get(artifact_type)
    if isinstance(body, dict):
        return body
    for key in ("formatted_draft", "polished_draft", "draft", "outline", "literature_report", "writing_task"):
        body = payload.get(key)
        if isinstance(body, dict):
            return body
    return payload if isinstance(payload, dict) else {}


def _path_from_payload_or_metadata(body: dict[str, Any], metadata: dict[str, Any], kind: str) -> str | None:
    key = {
        "markdown": "markdown_path",
        "docx": "docx_path",
        "pdf": "pdf_path",
    }[kind]
    value = body.get(key)
    if isinstance(value, str) and value.strip():
        return value
    value = metadata.get(key)
    if isinstance(value, str) and value.strip():
        return value
    return None


def _resolve_known_path(cfg: RuntimeConfig, raw_path: str | Path | None) -> Path | None:
    if raw_path is None:
        return None
    candidate = Path(raw_path)
    candidates = [candidate] if candidate.is_absolute() else [
        cfg.repo_root / candidate,
        cfg.project_root / candidate,
        cfg.artifact_root / candidate,
    ]
    for item in candidates:
        resolved = item.resolve()
        if resolved.exists():
            return resolved
    return candidates[0].resolve()


def _is_allowed_path(cfg: RuntimeConfig, path: Path) -> bool:
    resolved = path.resolve()
    for root in [cfg.repo_root, cfg.workspace_root, cfg.project_root, cfg.artifact_root]:
        try:
            resolved.relative_to(root.resolve())
        except ValueError:
            continue
        return True
    return False


def _looks_unsafe_segment(value: str) -> bool:
    return value in {"", ".", ".."} or "/" in value or "\\" in value
