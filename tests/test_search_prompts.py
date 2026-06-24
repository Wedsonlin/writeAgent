from __future__ import annotations

from pathlib import Path


def test_system_prompt_contains_search_evidence_policy():
    text = Path("skill_packs/academic-paper-writing/system_prompt.md").read_text(encoding="utf-8")

    assert "search_knowledge" in text
    assert "extract_sources" in text
    assert "search_evidence" in text


def test_literature_prompt_requires_search_when_references_are_insufficient():
    text = Path("config/agent_prompts/literature-review.md").read_text(encoding="utf-8")

    assert "task_book_markdown" in text
    assert "task_book_markdown_path" in text
    assert "JSON anchors" in text
    assert "core_arguments" in text
    assert "innovation_points" in text
    assert "argument_evidence_matrix" in text
    assert "literature-paper-reader-agent" in text
    assert "task" in text
    assert "3-5" in text
    assert "paper_reading_cards" in text
    assert "argument_support_matrix" in text
    assert "innovation_support_matrix" in text
    assert "research_keywords" in text
    assert "JSON" in text
    assert "Markdown" in text
    assert "文献梳理报告" in text
    assert "search_knowledge" in text
    assert "academic_papers" in text
    assert "extract_sources" in text
    assert "snippet" in text
    assert "references_seed" in text
    assert "Express generated report content in Chinese" in text
    assert "key_claims_zh" in text
    assert "timeline_summary_zh" in text
    assert "单独" in text
    assert "参考文献列表" in text
    assert "update_progress" not in text
    assert "update_artifact_manifest" not in text


def test_literature_paper_reader_prompt_outputs_reading_cards_only():
    text = Path("config/agent_prompts/literature-paper-reader.md").read_text(encoding="utf-8")

    assert "paper_reading_cards" in text
    assert "search_knowledge" in text
    assert "extract_sources" in text
    assert "source_artifact_ids" in text
    assert "main_claims_zh" in text
    assert "relevance_to_arguments" in text
    assert "relevance_to_innovations" in text
    assert "不要生成完整文献综述" in text
    assert "完整文献综述、文献梳理报告" in text


def test_content_generation_prompt_requires_search_for_unsupported_facts():
    text = Path("config/agent_prompts/content-generation.md").read_text(encoding="utf-8")

    assert "search_knowledge" in text
    assert "search_evidence" in text
    assert "literature_report" in text
