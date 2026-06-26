"""Tavily-backed knowledge search tool."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Literal

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


SearchIntent = Literal["academic_papers", "web_background", "recent_updates", "citation_metadata"]
SearchDepth = Literal["basic", "advanced", "fast", "ultra-fast"]


class SearchKnowledgeInput(BaseModel):
    queries: list[str] = Field(..., min_length=1, max_length=5)
    intent: SearchIntent = "web_background"
    stage_id: str | None = None
    max_results: int = Field(default=5, ge=1, le=20)
    depth_profile: SearchDepth | None = None
    time_range: str | None = None
    include_domains: list[str] = Field(default_factory=list)
    exclude_domains: list[str] = Field(default_factory=list)
    force_refresh: bool = False


def search_knowledge(
    queries: list[str],
    intent: SearchIntent = "web_background",
    stage_id: str | None = None,
    max_results: int = 5,
    depth_profile: SearchDepth | None = None,
    time_range: str | None = None,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    force_refresh: bool = False,
    *,
    artifact_root: str | Path = REPO_ROOT / ".writeagent" / "projects" / "default",
    manifest_path: str | Path | None = None,
    client: TavilyClient | None = None,
) -> dict[str, Any]:
    return asyncio.run(
        asearch_knowledge(
            queries=queries,
            intent=intent,
            stage_id=stage_id,
            max_results=max_results,
            depth_profile=depth_profile,
            time_range=time_range,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            force_refresh=force_refresh,
            artifact_root=artifact_root,
            manifest_path=manifest_path,
            client=client,
        )
    )


async def asearch_knowledge(
    queries: list[str],
    intent: SearchIntent = "web_background",
    stage_id: str | None = None,
    max_results: int = 5,
    depth_profile: SearchDepth | None = None,
    time_range: str | None = None,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    force_refresh: bool = False,
    *,
    artifact_root: str | Path = REPO_ROOT / ".writeagent" / "projects" / "default",
    manifest_path: str | Path | None = None,
    client: TavilyClient | None = None,
) -> dict[str, Any]:
    active_client = client or get_tavily_client()
    if not getattr(active_client, "is_available", False):
        return {"status": "unavailable", "reason": "TAVILY_API_KEY is not configured"}

    cleaned_queries = _clean_queries(queries)
    root = Path(artifact_root)
    manifest = Path(manifest_path) if manifest_path is not None else root / "artifacts" / "manifest.json"
    request_payload = {
        "queries": cleaned_queries,
        "intent": intent,
        "max_results": max_results,
        "depth_profile": depth_profile,
        "time_range": time_range,
        "include_domains": include_domains or [],
        "exclude_domains": exclude_domains or [],
    }
    cache_key = stable_cache_key("search", request_payload)
    cached = None if force_refresh else await asyncio.to_thread(read_cache, root, cache_key)
    if cached is not None:
        return await asyncio.to_thread(
            _persist_search_result,
            cached,
            status="cached",
            artifact_root=root,
            manifest_path=manifest,
            stage_id=stage_id,
            cache_hit=True,
        )

    try:
        call_payloads = [
            _build_search_payload(
                query=query,
                intent=intent,
                max_results=max_results,
                depth_profile=depth_profile,
                time_range=time_range,
                include_domains=include_domains or [],
                exclude_domains=exclude_domains or [],
            )
            for query in cleaned_queries
        ]
        responses = await asyncio.gather(
            *(active_client.search(payload) for payload in call_payloads),
            return_exceptions=True,
        )
    except Exception as exc:
        return {"status": "failed", "error": sanitize_error(exc, getattr(active_client, "api_key", None))}

    query_results: list[dict[str, Any]] = []
    all_results: list[dict[str, Any]] = []
    errors: list[str] = []
    for query, response in zip(cleaned_queries, responses):
        if isinstance(response, BaseException):
            errors.append(sanitize_error(response, getattr(active_client, "api_key", None)))
            query_results.append({"query": query, "status": "failed", "results": [], "error": errors[-1]})
            continue
        normalized = [_normalize_search_result(item, query) for item in response.get("results", [])]
        query_results.append(
            {
                "query": query,
                "status": "ok",
                "results": normalized,
                "request_id": response.get("request_id"),
                "usage": response.get("usage"),
                "response_time": response.get("response_time"),
            }
        )
        all_results.extend(normalized)

    if not all_results:
        return {"status": "failed", "error": "; ".join(errors) or "Tavily returned no results", "query_results": query_results}

    payload = {
        "artifact_type": ARTIFACT_TYPE,
        "evidence_kind": "search",
        "provider": "tavily",
        "intent": intent,
        "queries": cleaned_queries,
        "retrieved_at": utc_now(),
        "results": all_results,
        "query_results": query_results,
        "policy": {
            "cache_hit": False,
            "depth_profile": depth_profile or _default_depth(intent),
            "filters": {
                "time_range": time_range,
                "include_domains": include_domains or [],
                "exclude_domains": exclude_domains or [],
            },
            "max_results": max_results,
            "concurrency": len(cleaned_queries),
        },
    }
    await asyncio.to_thread(write_cache, root, cache_key, payload)
    status = "partial" if errors else "ok"
    return await asyncio.to_thread(
        _persist_search_result,
        payload,
        status=status,
        artifact_root=root,
        manifest_path=manifest,
        stage_id=stage_id,
        cache_hit=False,
    )


def _persist_search_result(
    payload: dict[str, Any],
    *,
    status: str,
    artifact_root: Path,
    manifest_path: Path,
    stage_id: str | None,
    cache_hit: bool,
) -> dict[str, Any]:
    evidence = json_ready(payload)
    evidence["policy"] = {**evidence.get("policy", {}), "cache_hit": cache_hit}
    artifact = write_evidence_artifact(
        artifact_root=artifact_root,
        manifest_path=manifest_path,
        evidence=evidence,
        stage_id=stage_id,
        created_by="search_knowledge",
        summary=f"Tavily search evidence for {', '.join(evidence.get('queries', [])[:2])}",
        metadata={"provider": "tavily", "intent": evidence.get("intent"), "cache_hit": cache_hit},
    )
    return _compact_search_result(evidence, artifact, status=status)


def _compact_search_result(
    evidence: dict[str, Any],
    artifact: dict[str, Any],
    *,
    status: str,
) -> dict[str, Any]:
    results = _dict_list(evidence.get("results"))
    queries = [str(query) for query in evidence.get("queries", []) if str(query).strip()]
    query_results = _dict_list(evidence.get("query_results"))
    failed_query_count = sum(1 for item in query_results if item.get("status") != "ok")
    compact: dict[str, Any] = {
        "status": status,
        "artifact": artifact,
        "result_count": len(results),
        "query_count": len(queries),
        "queries": queries,
        "preview_results": [_compact_search_preview(item) for item in results[:3]],
    }
    if failed_query_count:
        compact["failed_query_count"] = failed_query_count
    return compact


def _compact_search_preview(item: dict[str, Any]) -> dict[str, Any]:
    preview = {
        "title": item.get("title"),
        "url": item.get("url"),
        "domain": item.get("domain"),
        "score": item.get("score"),
    }
    return {key: value for key, value in preview.items() if value not in (None, "", [])}


def _dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _build_search_payload(
    *,
    query: str,
    intent: SearchIntent,
    max_results: int,
    depth_profile: SearchDepth | None,
    time_range: str | None,
    include_domains: list[str],
    exclude_domains: list[str],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "query": query,
        "search_depth": depth_profile or _default_depth(intent),
        "max_results": max_results,
        "topic": "general",
        "include_answer": False,
        "include_raw_content": False,
        "include_usage": True,
    }
    if time_range:
        payload["time_range"] = time_range
    if include_domains:
        payload["include_domains"] = include_domains
    if exclude_domains:
        payload["exclude_domains"] = exclude_domains
    if intent == "recent_updates" and not time_range:
        payload["time_range"] = "year"
    return payload


def _default_depth(intent: SearchIntent) -> SearchDepth:
    if intent in {"academic_papers", "citation_metadata"}:
        return "advanced"
    return "basic"


def _normalize_search_result(item: dict[str, Any], query: str) -> dict[str, Any]:
    url = str(item.get("url") or "")
    return {
        "query": query,
        "title": str(item.get("title") or ""),
        "url": url,
        "domain": domain_for_url(url),
        "content": item.get("content") or "",
        "snippet": item.get("content") or "",
        "raw_content": item.get("raw_content"),
        "score": item.get("score"),
        "source_type": "web",
        "favicon": item.get("favicon"),
    }


def _clean_queries(queries: list[str]) -> list[str]:
    cleaned = [" ".join(str(query).split()) for query in queries if str(query).strip()]
    if not cleaned:
        raise ValueError("queries must contain at least one non-empty query")
    if len(cleaned) > 5:
        raise ValueError("search_knowledge accepts at most 5 queries per call")
    for query in cleaned:
        if len(query) < 3 or len(query) > 400:
            raise ValueError("each query must be between 3 and 400 characters")
    return cleaned


def json_ready(payload: dict[str, Any]) -> dict[str, Any]:
    return dict(payload)
