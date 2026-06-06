"""ArtifactManifest persistence and query logic."""

from __future__ import annotations

import json
from pathlib import Path

from .schemas import ArtifactMeta


class ArtifactManifest:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.artifacts: dict[str, ArtifactMeta] = {}

    @classmethod
    def load(cls, path: str | Path) -> "ArtifactManifest":
        manifest = cls(path)
        if manifest.path.exists():
            data = json.loads(manifest.path.read_text(encoding="utf-8") or "{}")
            for item in data.get("artifacts", []):
                meta = ArtifactMeta.model_validate(item)
                manifest.artifacts[meta.artifact_id] = meta
        return manifest

    def save(self) -> None:
        payload = {"artifacts": [meta.model_dump() for meta in self.artifacts.values()]}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def upsert(self, meta: ArtifactMeta) -> ArtifactMeta:
        existing = self.artifacts.get(meta.artifact_id)
        if existing is not None:
            data = existing.model_dump()
            incoming = meta.model_dump(exclude_unset=True)
            data.update(incoming)
            data["version"] = existing.version + 1
            meta = ArtifactMeta.model_validate(data)
        self.artifacts[meta.artifact_id] = meta
        self.save()
        return meta

    def update_summary(self, artifact_id: str, summary: str) -> ArtifactMeta:
        if artifact_id not in self.artifacts:
            raise KeyError(f"Unknown artifact: {artifact_id}")
        meta = self.artifacts[artifact_id].model_copy(update={"summary": summary, "version": self.artifacts[artifact_id].version + 1})
        self.artifacts[artifact_id] = meta
        self.save()
        return meta

    def get(self, artifact_id: str) -> ArtifactMeta | None:
        return self.artifacts.get(artifact_id)

    def list_by_type(self, artifact_type: str) -> list[ArtifactMeta]:
        return [meta for meta in self.artifacts.values() if meta.artifact_type == artifact_type]

    def has_type(self, artifact_type: str) -> bool:
        return any(meta.artifact_type == artifact_type for meta in self.artifacts.values())

    def latest_by_type(self, artifact_type: str) -> ArtifactMeta | None:
        items = self.list_by_type(artifact_type)
        return items[-1] if items else None
