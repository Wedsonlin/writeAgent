from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from artifacts.manifest import ArtifactManifest
from tools.extract_sources import aextract_sources
from tools.search_knowledge import asearch_knowledge


class FakeUnavailableClient:
    is_available = False
    api_key = None


class FakeSearchClient:
    is_available = True
    api_key = "fake-key"

    def __init__(self, delay: float = 0.0) -> None:
        self.delay = delay
        self.calls: list[dict] = []
        self.active = 0
        self.max_active = 0

    async def search(self, payload: dict) -> dict:
        self.calls.append(payload)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
            query = payload["query"]
            return {
                "query": query,
                "response_time": 0.01,
                "results": [
                    {
                        "title": f"Result for {query}",
                        "url": f"https://example.com/{query.replace(' ', '-')}",
                        "content": f"Snippet about {query}",
                        "score": 0.9,
                    }
                ],
            }
        finally:
            self.active -= 1


class FakeExtractClient:
    is_available = True
    api_key = "fake-key"

    def __init__(self, delay: float = 0.0) -> None:
        self.delay = delay
        self.calls: list[dict] = []
        self.active = 0
        self.max_active = 0

    async def extract(self, payload: dict) -> dict:
        self.calls.append(payload)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
            url = payload["urls"][0]
            return {
                "response_time": 0.01,
                "results": [
                    {
                        "url": url,
                        "raw_content": f"Full extracted content from {url}",
                    }
                ],
                "failed_results": [],
            }
        finally:
            self.active -= 1


class FakeFailingClient:
    is_available = True
    api_key = "super-secret-token"

    async def search(self, _payload: dict) -> dict:
        raise RuntimeError("provider failed with super-secret-token")


def test_search_without_api_key_returns_unavailable_without_artifact(tmp_path: Path):
    result = asyncio.run(
        asearch_knowledge(
            queries=["agentic writing"],
            intent="web_background",
            artifact_root=tmp_path,
            manifest_path=tmp_path / "manifest.json",
            client=FakeUnavailableClient(),
        )
    )

    assert result["status"] == "unavailable"
    assert "artifact" not in result
    assert not (tmp_path / "manifest.json").exists()


def test_search_writes_search_evidence_artifact_and_manifest(tmp_path: Path):
    result = asyncio.run(
        asearch_knowledge(
            queries=["agentic academic writing"],
            intent="academic_papers",
            stage_id="literature_review",
            artifact_root=tmp_path,
            manifest_path=tmp_path / "manifest.json",
            client=FakeSearchClient(),
        )
    )

    assert result["status"] == "ok"
    assert result["artifact"]["artifact_type"] == "search_evidence"
    payload = json.loads((tmp_path / result["artifact"]["path"]).read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "search_evidence"
    assert payload["provider"] == "tavily"
    assert payload["intent"] == "academic_papers"
    assert payload["queries"] == ["agentic academic writing"]
    assert payload["results"][0]["title"] == "Result for agentic academic writing"

    manifest = ArtifactManifest.load(tmp_path / "manifest.json")
    saved = manifest.get(result["artifact"]["artifact_id"])
    assert saved is not None
    assert saved.artifact_type == "search_evidence"
    assert saved.stage_id == "literature_review"


def test_search_runs_multiple_queries_concurrently_and_maps_intent(tmp_path: Path):
    client = FakeSearchClient(delay=0.05)
    started = time.perf_counter()

    result = asyncio.run(
        asearch_knowledge(
            queries=["agentic writing", "literature review"],
            intent="academic_papers",
            max_results=2,
            artifact_root=tmp_path,
            manifest_path=tmp_path / "manifest.json",
            client=client,
        )
    )

    elapsed = time.perf_counter() - started
    assert result["status"] == "ok"
    assert client.max_active == 2
    assert elapsed < 0.09
    assert [call["query"] for call in client.calls] == ["agentic writing", "literature review"]
    assert all(call["search_depth"] == "advanced" for call in client.calls)
    assert all(call["max_results"] == 2 for call in client.calls)
    assert len(result["results"]) == 2


def test_search_cache_avoids_duplicate_provider_calls(tmp_path: Path):
    client = FakeSearchClient()
    kwargs = {
        "queries": ["cached query"],
        "intent": "web_background",
        "artifact_root": tmp_path,
        "manifest_path": tmp_path / "manifest.json",
        "client": client,
    }

    first = asyncio.run(asearch_knowledge(**kwargs))
    second = asyncio.run(asearch_knowledge(**kwargs))

    assert first["status"] == "ok"
    assert second["status"] == "cached"
    assert len(client.calls) == 1
    assert second["results"][0]["url"] == "https://example.com/cached-query"


def test_extract_sources_runs_concurrently_and_depends_on_source_artifact(tmp_path: Path):
    client = FakeExtractClient(delay=0.05)
    started = time.perf_counter()

    result = asyncio.run(
        aextract_sources(
            urls=["https://example.com/a", "https://example.com/b"],
            stage_id="literature_review",
            source_artifact_id="search-1",
            reason="verify source text",
            artifact_root=tmp_path,
            manifest_path=tmp_path / "manifest.json",
            client=client,
        )
    )

    elapsed = time.perf_counter() - started
    assert result["status"] == "ok"
    assert client.max_active == 2
    assert elapsed < 0.09
    assert len(result["results"]) == 2

    manifest = ArtifactManifest.load(tmp_path / "manifest.json")
    saved = manifest.get(result["artifact"]["artifact_id"])
    assert saved is not None
    assert saved.depends_on == ["search-1"]


def test_search_failure_sanitizes_api_key(tmp_path: Path):
    result = asyncio.run(
        asearch_knowledge(
            queries=["will fail"],
            intent="web_background",
            artifact_root=tmp_path,
            manifest_path=tmp_path / "manifest.json",
            client=FakeFailingClient(),
        )
    )

    rendered = json.dumps(result, ensure_ascii=False)
    assert result["status"] == "failed"
    assert "super-secret-token" not in rendered
    assert "provider failed" in rendered
