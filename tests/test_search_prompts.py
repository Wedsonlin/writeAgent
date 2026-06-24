from __future__ import annotations

from pathlib import Path


def test_system_prompt_contains_search_evidence_policy():
    text = Path("skill_packs/academic-paper-writing/system_prompt.md").read_text(encoding="utf-8")

    assert "search_knowledge" in text
    assert "extract_sources" in text
    assert "search_evidence" in text


def test_literature_prompt_requires_search_when_references_are_insufficient():
    text = Path("config/agent_prompts/literature-review.md").read_text(encoding="utf-8")

    assert "search_knowledge" in text
    assert "academic_papers" in text
    assert "extract_sources" in text
    assert "references_seed" in text


def test_content_generation_prompt_requires_search_for_unsupported_facts():
    text = Path("config/agent_prompts/content-generation.md").read_text(encoding="utf-8")

    assert "search_knowledge" in text
    assert "search_evidence" in text
    assert "literature_report" in text
