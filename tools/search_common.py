"""Shared helpers for search/evidence tools."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from artifacts.manifest import ArtifactManifest
from artifacts.schemas import ArtifactMeta


ARTIFACT_TYPE = "search_evidence"
_WRITE_LOCK = threading.Lock()


def cache_ttl_days() -> int:
    return int(os.getenv("WRITEAGENT_SEARCH_CACHE_TTL_DAYS", "30"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def domain_for_url(url: str) -> str:
    return urlparse(url).netloc.lower()


def sanitize_error(error: BaseException | str, api_key: str | None = None) -> str:
    text = str(error)
    if api_key:
        text = text.replace(api_key, "[redacted]")
    return text


def stable_cache_key(endpoint: str, payload: dict[str, Any]) -> str:
    rendered = json.dumps({"endpoint": endpoint, "payload": payload}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def read_cache(artifact_root: str | Path, key: str, ttl_days: int | None = None) -> dict[str, Any] | None:
    path = _cache_path(artifact_root, key)
    if not path.exists():
        return None
    ttl = ttl_days if ttl_days is not None else cache_ttl_days()
    if ttl >= 0:
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        if datetime.now(timezone.utc) - modified > timedelta(days=ttl):
            return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_cache(artifact_root: str | Path, key: str, payload: dict[str, Any]) -> None:
    path = _cache_path(artifact_root, key)
    _atomic_write_json(path, payload)


def write_evidence_artifact(
    *,
    artifact_root: str | Path,
    manifest_path: str | Path,
    evidence: dict[str, Any],
    stage_id: str | None,
    created_by: str,
    summary: str,
    depends_on: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(artifact_root)
    artifact_id = f"search-evidence-{uuid4().hex[:12]}"
    relative_path = Path("search_evidence") / f"{artifact_id}.json"
    artifact_path = root / relative_path
    payload = {"artifact_id": artifact_id, **evidence}

    with _WRITE_LOCK:
        _atomic_write_json(artifact_path, payload)
        manifest = ArtifactManifest.load(manifest_path)
        saved = manifest.upsert(
            ArtifactMeta(
                artifact_id=artifact_id,
                artifact_type=ARTIFACT_TYPE,
                schema_name="search-evidence.v1",
                path=str(relative_path).replace("\\", "/"),
                summary=summary,
                stage_id=stage_id,
                created_by=created_by,
                depends_on=depends_on or [],
                metadata=metadata or {},
            )
        )
    return saved.model_dump()


def _cache_path(artifact_root: str | Path, key: str) -> Path:
    return Path(artifact_root) / "_search_cache" / f"{key}.json"


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{uuid4().hex}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
