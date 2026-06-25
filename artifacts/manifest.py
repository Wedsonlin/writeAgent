"""ArtifactManifest persistence and query logic."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from .schemas import ArtifactMeta

_PATH_LOCKS: dict[str, threading.RLock] = {}
_PATH_LOCKS_GUARD = threading.Lock()


def _lock_for(path: Path) -> threading.RLock:
    key = str(path.resolve())
    with _PATH_LOCKS_GUARD:
        lock = _PATH_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _PATH_LOCKS[key] = lock
        return lock


def _read_manifest_payload(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        payload, _ = decoder.raw_decode(raw)
        if isinstance(payload, dict):
            return payload
        raise


class ArtifactManifest:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.artifacts: dict[str, ArtifactMeta] = {}

    @classmethod
    def load(cls, path: str | Path) -> "ArtifactManifest":
        manifest = cls(path)
        with _lock_for(manifest.path):
            manifest._reload_unlocked()
        return manifest

    def _reload_unlocked(self) -> None:
        self.artifacts = {}
        if self.path.exists():
            data = _read_manifest_payload(self.path)
            for item in data.get("artifacts", []):
                meta = ArtifactMeta.model_validate(item)
                self.artifacts[meta.artifact_id] = meta

    def save(self) -> None:
        with _lock_for(self.path):
            payload = {"artifacts": [meta.model_dump() for meta in self.artifacts.values()]}
            tmp_path = self.path.with_name(f"{self.path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
            tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp_path, self.path)

    def upsert(self, meta: ArtifactMeta) -> ArtifactMeta:
        with _lock_for(self.path):
            self._reload_unlocked()
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
        with _lock_for(self.path):
            self._reload_unlocked()
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
