"""Artifact retrieval helpers."""

from __future__ import annotations

from .manifest import ArtifactManifest
from .schemas import ArtifactMeta


def find_artifacts(manifest: ArtifactManifest, artifact_type: str | None = None) -> list[ArtifactMeta]:
    if artifact_type is None:
        return list(manifest.artifacts.values())
    return manifest.list_by_type(artifact_type)
