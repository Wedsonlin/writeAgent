from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from tools.extract_sources import aextract_sources
from tools.search_knowledge import asearch_knowledge


pytestmark = pytest.mark.integration


def test_real_tavily_search_and_extract_writes_evidence(tmp_path: Path):
    if not os.getenv("TAVILY_API_KEY"):
        pytest.skip("TAVILY_API_KEY is not configured")

    search = asyncio.run(
        asearch_knowledge(
            queries=["agentic academic writing literature review", "Tavily search API academic papers"],
            intent="academic_papers",
            max_results=2,
            stage_id="literature_review",
            artifact_root=tmp_path,
            manifest_path=tmp_path / "manifest.json",
            force_refresh=True,
        )
    )

    assert search["status"] == "ok"
    assert search["artifact"]["artifact_type"] == "search_evidence"
    assert len(search["query_results"]) == 2
    assert all(item["results"] for item in search["query_results"])
    first = search["query_results"][0]["results"][0]
    assert first["title"]
    assert first["url"].startswith("http")

    extract = asyncio.run(
        aextract_sources(
            urls=[first["url"]],
            stage_id="literature_review",
            source_artifact_id=search["artifact"]["artifact_id"],
            reason="integration test extraction",
            artifact_root=tmp_path,
            manifest_path=tmp_path / "manifest.json",
            force_refresh=True,
        )
    )

    assert extract["status"] in {"ok", "partial", "failed"}
    if extract["status"] in {"ok", "partial"}:
        assert extract["artifact"]["artifact_type"] == "search_evidence"
        assert extract["results"][0]["url"].startswith("http")
        assert extract["results"][0].get("raw_content") or extract["results"][0].get("content")
    else:
        assert extract["error"]
