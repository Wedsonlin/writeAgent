"""Tavily-backed source extraction tool."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agent_core.config import REPO_ROOT
from .search_common import (
    ARTIFACT_TYPE,
    domain_for_url,
    read_cache,
    sanitize_error,
    stable_cache_key,
    utc_now,
    write_cache,
    write_evidence_artifact,
)
from .tavily_client import TavilyClient, get_tavily_client


class ExtractSourcesInput(BaseModel):
    urls: list[str] = Field(..., min_length=1, max_length=5)
    stage_id: str | None = None
    source_artifact_id: str | None = None
    reason: str | None = None
    force_refresh: bool = False


def extract_sources(
    urls: list[str],
    stage_id: str | None = None,
    source_artifact_id: str | None = None,
    reason: str | None = None,
    force_refresh: bool = False,
    *,
    artifact_root: str | Path = REPO_ROOT / ".writeagent" / "projects" / "default",
    manifest_path: str | Path | None = None,
    client: TavilyClient | None = None,
) -> dict[str, Any]:
    return asyncio.run(
        aextract_sources(
            urls=urls,
            stage_id=stage_id,
            source_artifact_id=source_artifact_id,
            reason=reason,
            force_refresh=force_refresh,
            artifact_root=artifact_root,
            manifest_path=manifest_path,
            client=client,
        )
    )


async def aextract_sources(
    urls: list[str],
    stage_id: str | None = None,
    source_artifact_id: str | None = None,
    reason: str | None = None,
    force_refresh: bool = False,
    *,
    artifact_root: str | Path = REPO_ROOT / ".writeagent" / "projects" / "default",
    manifest_path: str | Path | None = None,
    client: TavilyClient | None = None,
) -> dict[str, Any]:
    active_client = client or get_tavily_client()
    if not getattr(active_client, "is_available", False):
        return {"status": "unavailable", "reason": "TAVILY_API_KEY is not configured"}

    cleaned_urls = _clean_urls(urls)
    root = Path(artifact_root)
    manifest = Path(manifest_path) if manifest_path is not None else root / "artifacts" / "manifest.json"
    request_payload = {"urls": cleaned_urls, "reason": reason}
    cache_key = stable_cache_key("extract", request_payload)
    cached = None if force_refresh else await asyncio.to_thread(read_cache, root, cache_key)
    if cached is not None:
        return await asyncio.to_thread(
            _persist_extract_result,
            cached,
            status="cached",
            artifact_root=root,
            manifest_path=manifest,
            stage_id=stage_id,
            source_artifact_id=source_artifact_id,
            cache_hit=True,
        )

    responses = await asyncio.gather(
        *(active_client.extract(_build_extract_payload(url, reason)) for url in cleaned_urls),
        return_exceptions=True,
    )
    results: list[dict[str, Any]] = []
    failed_results: list[dict[str, Any]] = []
    errors: list[str] = []
    for url, response in zip(cleaned_urls, responses):
        if isinstance(response, BaseException):
            error = sanitize_error(response, getattr(active_client, "api_key", None))
            errors.append(error)
            failed_results.append({"url": url, "error": error})
            continue
        normalized = [_normalize_extract_result(item) for item in response.get("results", [])]
        results.extend(normalized)
        for failed in response.get("failed_results", []):
            failed_results.append(
                {
                    "url": failed.get("url") or url,
                    "error": sanitize_error(failed.get("error") or failed.get("message") or "extract failed"),
                }
            )

    if not results:
        return {
            "status": "failed",
            "error": "; ".join(errors) or "Tavily extract returned no content",
            "results": [],
            "failed_results": failed_results,
        }

    payload = {
        "artifact_type": ARTIFACT_TYPE,
        "evidence_kind": "extract",
        "provider": "tavily",
        "urls": cleaned_urls,
        "reason": reason,
        "retrieved_at": utc_now(),
        "results": results,
        "failed_results": failed_results,
        "policy": {
            "cache_hit": False,
            "extract_depth": "basic",
            "format": "markdown",
            "concurrency": len(cleaned_urls),
        },
    }
    await asyncio.to_thread(write_cache, root, cache_key, payload)
    status = "partial" if failed_results else "ok"
    return await asyncio.to_thread(
        _persist_extract_result,
        payload,
        status=status,
        artifact_root=root,
        manifest_path=manifest,
        stage_id=stage_id,
        source_artifact_id=source_artifact_id,
        cache_hit=False,
    )


def _persist_extract_result(
    payload: dict[str, Any],
    *,
    status: str,
    artifact_root: Path,
    manifest_path: Path,
    stage_id: str | None,
    source_artifact_id: str | None,
    cache_hit: bool,
) -> dict[str, Any]:
    evidence = dict(payload)
    evidence["policy"] = {**evidence.get("policy", {}), "cache_hit": cache_hit}
    artifact = write_evidence_artifact(
        artifact_root=artifact_root,
        manifest_path=manifest_path,
        evidence=evidence,
        stage_id=stage_id,
        created_by="extract_sources",
        summary=f"Tavily extract evidence for {len(evidence.get('urls', []))} URL(s)",
        depends_on=[source_artifact_id] if source_artifact_id else [],
        metadata={"provider": "tavily", "evidence_kind": "extract", "cache_hit": cache_hit},
    )
    return _compact_extract_result(evidence, artifact, status=status)


def _compact_extract_result(
    evidence: dict[str, Any],
    artifact: dict[str, Any],
    *,
    status: str,
) -> dict[str, Any]:
    results = _dict_list(evidence.get("results"))
    failed_results = _dict_list(evidence.get("failed_results"))
    urls = [str(url) for url in evidence.get("urls", []) if str(url).strip()]
    return {
        "status": status,
        "artifact": artifact,
        "result_count": len(results),
        "failed_count": len(failed_results),
        "urls": urls,
        "preview_results": [_compact_extract_preview(item) for item in results[:3]],
    }


def _compact_extract_preview(item: dict[str, Any]) -> dict[str, Any]:
    content = str(item.get("content") or item.get("raw_content") or "")
    preview = {
        "url": item.get("url"),
        "domain": item.get("domain"),
        "content_chars": len(content),
    }
    return {key: value for key, value in preview.items() if value not in (None, "", [])}


def _dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _build_extract_payload(url: str, reason: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "urls": [url],
        "extract_depth": "basic",
        "format": "markdown",
        "include_usage": True,
    }
    if reason:
        payload["query"] = reason
        payload["chunks_per_source"] = 3
    return payload


def _normalize_extract_result(item: dict[str, Any]) -> dict[str, Any]:
    url = str(item.get("url") or "")
    return {
        "url": url,
        "domain": domain_for_url(url),
        "raw_content": item.get("raw_content") or "",
        "content": item.get("raw_content") or "",
        "source_type": "web_extract",
        "favicon": item.get("favicon"),
        "images": item.get("images") or [],
    }


def _clean_urls(urls: list[str]) -> list[str]:
    cleaned = [" ".join(str(url).split()) for url in urls if str(url).strip()]
    if not cleaned:
        raise ValueError("urls must contain at least one URL")
    if len(cleaned) > 5:
        raise ValueError("extract_sources accepts at most 5 URLs per call")
    for url in cleaned:
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError("extract_sources only accepts http(s) URLs")
    return cleaned
