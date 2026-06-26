"""Tool for inspecting workflow progress."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from artifacts.manifest import ArtifactManifest
from project_store.ledger import ProgressLedger


def inspect_progress(
    progress_path: str | Path,
    manifest_path: str | Path,
    *,
    project_id: str | None = None,
    project_root: str | Path | None = None,
    artifact_root: str | Path | None = None,
    tmp_root: str | Path | None = None,
    evidence_root: str | Path | None = None,
    cache_root: str | Path | None = None,
) -> dict[str, Any]:
    ledger = ProgressLedger.load(progress_path)
    manifest = ArtifactManifest.load(manifest_path)
    payload = {
        "status": "ok",
        "project_id": project_id,
        "current_stage": ledger.current_stage,
        "completed_stages": ledger.completed_stages(),
        "pending_stages": ledger.pending_stages(),
        "blocked_reason": ledger.blocked_reason,
        "artifacts": [meta.model_dump() for meta in manifest.artifacts.values()],
        "next_recommended_action": ledger.current_stage or ledger.next_recommended_stage(),
    }
    if project_root is not None:
        payload["paths"] = {
            "project_root": str(project_root),
            "artifact_root": str(artifact_root),
            "tmp_root": str(tmp_root),
            "evidence_root": str(evidence_root),
            "cache_root": str(cache_root),
        }
    return payload
