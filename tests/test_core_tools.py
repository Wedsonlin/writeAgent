from __future__ import annotations

import asyncio
import json
from pathlib import Path

from artifacts.manifest import ArtifactManifest
from tools.extract_sources import aextract_sources
from tools.search_common import write_cache
from tools.search_knowledge import asearch_knowledge
import tools.extract_sources as extract_sources_module
import tools.search_knowledge as search_knowledge_module


class FakeSearchClient:
    is_available = True
    api_key = "fake-key"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def search(self, payload: dict) -> dict:
        self.calls.append(payload)
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


class FakeExtractClient:
    is_available = True
    api_key = "fake-key"

    async def extract(self, payload: dict) -> dict:
        url = payload["urls"][0]
        return {
            "response_time": 0.01,
            "results": [{"url": url, "raw_content": f"Full extracted content from {url}"}],
            "failed_results": [],
        }


class FakeFailingClient:
    is_available = True
    api_key = "super-secret-token"

    async def search(self, _payload: dict) -> dict:
        raise RuntimeError("provider failed with super-secret-token")


def test_atomic_write_tmp_name_avoids_windows_max_path():
    key = "b738ace948d8e95135f30a4b2d9c4f070f5c716686867ba4b1e517ad34951330"
    root = Path(
        r"C:\Users\Administrator\Desktop\thesis\高级人工智能\finalAssignment\writeAgent"
        r"\.writeagent\projects\20260626-152358_thread-cdd8f114-7b87-4fc2-96f9-7e53222b1357"
    )
    target = root / "cache" / "search" / f"{key[:32]}.json"
    legacy_tmp = (root / "cache" / "search" / f"{key}.json").with_suffix(".json." + "a" * 32 + ".tmp")
    short_tmp = target.parent / f".{'a' * 32}.tmp"
    assert len(str(target)) < 260
    assert len(str(legacy_tmp)) > 260
    assert len(str(short_tmp)) < len(str(legacy_tmp))


def test_write_cache_with_sha256_key(tmp_path: Path):
    key = "b738ace948d8e95135f30a4b2d9c4f070f5c716686867ba4b1e517ad34951330"
    write_cache(tmp_path, key, {"cached": True})
    cache_file = tmp_path / "cache" / "search" / f"{key[:32]}.json"
    assert cache_file.exists()
    assert json.loads(cache_file.read_text(encoding="utf-8"))["cached"] is True
    assert list(cache_file.parent.glob(".*.tmp")) == []


def test_search_knowledge_persists_compact_evidence_manifest_and_cache(tmp_path: Path):
    client = FakeSearchClient()
    kwargs = {
        "queries": ["compact result payload"],
        "intent": "academic_papers",
        "stage_id": "literature_review",
        "artifact_root": tmp_path,
        "manifest_path": tmp_path / "manifest.json",
        "client": client,
    }

    first = asyncio.run(asearch_knowledge(**kwargs))
    second = asyncio.run(asearch_knowledge(**kwargs))

    assert first["status"] == "ok"
    assert second["status"] == "cached"
    assert len(client.calls) == 1
    assert first["artifact"]["path"].startswith("evidence/")
    assert "results" not in first
    assert first["preview_results"][0]["url"] == "https://example.com/compact-result-payload"

    payload = json.loads((tmp_path / first["artifact"]["path"]).read_text(encoding="utf-8"))
    assert payload["results"][0]["content"] == "Snippet about compact result payload"
    assert (tmp_path / "cache" / "search").exists()

    saved = ArtifactManifest.load(tmp_path / "manifest.json").get(first["artifact"]["artifact_id"])
    assert saved is not None
    assert saved.stage_id == "literature_review"


def test_extract_sources_persists_compact_evidence_and_dependency(tmp_path: Path):
    result = asyncio.run(
        aextract_sources(
            urls=["https://example.com/full"],
            stage_id="literature_review",
            source_artifact_id="search-1",
            artifact_root=tmp_path,
            manifest_path=tmp_path / "manifest.json",
            client=FakeExtractClient(),
        )
    )

    assert result["status"] == "ok"
    assert result["result_count"] == 1
    assert result["artifact"]["path"].startswith("evidence/")
    assert "results" not in result
    assert result["preview_results"][0]["content_chars"] == len("Full extracted content from https://example.com/full")

    payload = json.loads((tmp_path / result["artifact"]["path"]).read_text(encoding="utf-8"))
    assert payload["results"][0]["content"] == "Full extracted content from https://example.com/full"
    saved = ArtifactManifest.load(tmp_path / "manifest.json").get(result["artifact"]["artifact_id"])
    assert saved is not None
    assert saved.depends_on == ["search-1"]


def test_async_search_and_extract_persistence_run_outside_event_loop(monkeypatch, tmp_path: Path):
    calls: list[str] = []

    def record(label: str) -> None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            calls.append(label)
            return
        raise AssertionError(f"{label} ran in the event loop thread")

    monkeypatch.setattr(search_knowledge_module, "read_cache", lambda *_args, **_kwargs: (record("search_read"), None)[1])
    monkeypatch.setattr(search_knowledge_module, "write_cache", lambda *_args, **_kwargs: record("search_write"))
    monkeypatch.setattr(
        search_knowledge_module,
        "_persist_search_result",
        lambda payload, **_kwargs: (
            record("search_persist"),
            {"status": "ok", "artifact": {"artifact_id": "s", "artifact_type": "search_evidence", "path": "x.json"}, "preview_results": []},
        )[1],
    )
    monkeypatch.setattr(extract_sources_module, "read_cache", lambda *_args, **_kwargs: (record("extract_read"), None)[1])
    monkeypatch.setattr(extract_sources_module, "write_cache", lambda *_args, **_kwargs: record("extract_write"))
    monkeypatch.setattr(
        extract_sources_module,
        "_persist_extract_result",
        lambda payload, **_kwargs: (
            record("extract_persist"),
            {"status": "ok", "artifact": {"artifact_id": "e", "artifact_type": "extract_evidence", "path": "x.json"}, "preview_results": []},
        )[1],
    )

    asyncio.run(
        asearch_knowledge(
            queries=["threaded persistence"],
            artifact_root=tmp_path,
            manifest_path=tmp_path / "manifest.json",
            client=FakeSearchClient(),
        )
    )
    asyncio.run(
        aextract_sources(
            urls=["https://example.com/threaded"],
            artifact_root=tmp_path,
            manifest_path=tmp_path / "manifest.json",
            client=FakeExtractClient(),
        )
    )

    assert calls == [
        "search_read",
        "search_write",
        "search_persist",
        "extract_read",
        "extract_write",
        "extract_persist",
    ]


def test_search_failure_sanitizes_api_key(tmp_path: Path):
    result = asyncio.run(
        asearch_knowledge(
            queries=["will fail"],
            artifact_root=tmp_path,
            manifest_path=tmp_path / "manifest.json",
            client=FakeFailingClient(),
        )
    )

    rendered = json.dumps(result, ensure_ascii=False)
    assert result["status"] == "failed"
    assert "super-secret-token" not in rendered
    assert "provider failed" in rendered
