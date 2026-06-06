"""Tool for updating ArtifactManifest."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from artifacts.manifest import ArtifactManifest
from artifacts.schemas import ArtifactMeta
from traces.store import TraceStore


class UpdateArtifactManifestInput(BaseModel):
    artifact_id: str
    artifact_type: str
    path: str
    schema_name: str | None = None
    summary: str | None = None
    stage_id: str | None = None
    created_by: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


def update_artifact_manifest(
    manifest_path: str | Path,
    artifact_id: str,
    artifact_type: str,
    path: str,
    schema_name: str | None = None,
    summary: str | None = None,
    stage_id: str | None = None,
    created_by: str | None = None,
    depends_on: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    *,
    trace_store: TraceStore | None = None,
) -> dict[str, Any]:
    manifest = ArtifactManifest.load(manifest_path)
    meta = ArtifactMeta(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        schema_name=schema_name,
        path=path,
        summary=summary,
        stage_id=stage_id,
        created_by=created_by,
        depends_on=depends_on or [],
        metadata=metadata or {},
    )
    saved = manifest.upsert(meta)
    payload = {"status": "ok", "artifact": saved.model_dump()}
    if trace_store is not None:
        trace_store.append("artifact_update", payload=payload)
    return payload
