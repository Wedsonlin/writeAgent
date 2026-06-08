"""Custom HTTP routes mounted beside the LangGraph API."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from agent_core.config import RuntimeConfig
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


def _config() -> RuntimeConfig:
    return RuntimeConfig()
