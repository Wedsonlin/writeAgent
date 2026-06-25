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


def test_paper_outline_prompt_uses_task_and_literature_artifacts_without_harness_steps():
    text = Path("config/agent_prompts/paper-outline.md").read_text(encoding="utf-8")

    assert "task_book_markdown" in text
    assert "task_book_markdown_path" in text
    assert "literature_report_markdown" in text
    assert "literature_report_markdown_path" in text
    assert "writing_task" in text
    assert "literature_report" in text
    assert "core_arguments" in text
    assert "innovation_points" in text
    assert "argument_evidence_matrix" in text
    assert "argument_support_matrix" in text
    assert "innovation_support_matrix" in text
    assert "research_gaps" in text
    assert "structure_rationale" in text
    assert "logic_graph" in text
    assert "argument_coverage" in text
    assert "innovation_coverage" in text
    assert "outline_markdown" in text
    assert "outline_markdown_path" in text
    assert "Do not merely restate" in text
    assert "update_progress" not in text
    assert "update_artifact_manifest" not in text
    assert "cwd=\"/\"" not in text


def test_content_generation_prompt_requires_search_for_unsupported_facts():
    text = Path("config/agent_prompts/content-generation.md").read_text(encoding="utf-8")

    assert "outline_markdown" in text
    assert "outline_markdown_path" in text
    assert "literature_report_markdown" in text
    assert "literature_report_markdown_path" in text
    assert "section drafting card" in text
    assert "content-section-writer-agent" in text
    assert "core_arguments" in text
    assert "innovation_points" in text
    assert "argument_coverage" in text
    assert "innovation_coverage" in text
    assert "argument_support_matrix" in text
    assert "innovation_support_matrix" in text
    assert "paper_reading_cards" in text
    assert "draft_markdown" in text
    assert "draft_markdown_path" in text
    assert "unsupported_claims" in text
    assert "open_questions" in text
    assert "section_depth_checks" in text
    assert "mechanism" in text
    assert "comparison" in text
    assert "limitation" in text
    assert "argument_return" in text
    assert "Chinese academic prose" in text
    assert "[n]" in text
    assert "search_knowledge" in text
    assert "extract_sources" in text
    assert "search_evidence" in text
    assert "literature_report" in text
    assert "update_progress" not in text
    assert "update_artifact_manifest" not in text
    assert "cwd=\"/\"" not in text


def test_content_section_writer_prompt_outputs_sections_only():
    text = Path("config/agent_prompts/content-section-writer.md").read_text(encoding="utf-8")

    assert "section drafting card" in text
    assert "section_drafts" in text
    assert "evidence_used" in text
    assert "citations_used" in text
    assert "section_depth_checks" in text
    assert "mechanism_explained" in text
    assert "comparison_or_tradeoff" in text
    assert "argument_return" in text
    assert "linked_core_arguments" in text
    assert "linked_innovation_points" in text
    assert "Do not produce the final draft artifact" in text
    assert "Do not generate a complete paper" in text
    assert "artifact_type" not in text


def test_academic_formatting_prompt_exports_documents_without_harness_steps():
    text = Path("config/agent_prompts/academic-formatting.md").read_text(encoding="utf-8")

    assert "draft_markdown" in text
    assert "formatting_constraints" in text
    assert "target template" in text
    assert "formatted_draft" in text
    assert "docx_path" in text
    assert "pdf_path" in text
    assert "export_status" in text
    assert "format_check_report" in text
    assert "figure" in text
    assert "table" in text
    assert "Do not polish" in text
    assert "update_progress" not in text
    assert "update_artifact_manifest" not in text
    assert "cwd=\"/\"" not in text


def test_polish_prompt_exports_final_draft_and_preserves_claims_without_harness_steps():
    text = Path("config/agent_prompts/polish-plagiarism.md").read_text(encoding="utf-8")

    assert "formatted_draft" in text
    assert "polished_draft" in text
    assert "docx_path" in text
    assert "pdf_path" in text
    assert "export_status" in text
    assert "polish_log" in text
    assert "plagiarism_optimization" in text
    assert "protected claims" in text
    assert "citation" in text
    assert "reference block" in text
    assert "Do not change" in text
    assert "update_progress" not in text
    assert "update_artifact_manifest" not in text
    assert "cwd=\"/\"" not in text
