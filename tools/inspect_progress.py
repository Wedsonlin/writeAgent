"""Tool for inspecting workflow progress."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from artifacts.manifest import ArtifactManifest
from project_store.ledger import ProgressLedger


def inspect_progress(progress_path: str | Path, manifest_path: str | Path) -> dict[str, Any]:
    ledger = ProgressLedger.load(progress_path)
    manifest = ArtifactManifest.load(manifest_path)
    return {
        "status": "ok",
        "current_stage": ledger.current_stage,
        "completed_stages": ledger.completed_stages(),
        "pending_stages": ledger.pending_stages(),
        "blocked_reason": ledger.blocked_reason,
        "artifacts": [meta.model_dump() for meta in manifest.artifacts.values()],
        "next_recommended_action": ledger.current_stage or ledger.next_recommended_stage(),
    }
