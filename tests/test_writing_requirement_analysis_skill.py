from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run_script(repo_root: Path, input_path: Path, output_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repo_root / "skill_packs" / "academic-paper-writing" / "skills" / "writing-requirement-analysis" / "scripts" / "run.py"),
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_writing_requirement_analysis_outputs_contract_and_task_book(tmp_path):
    repo_root = Path.cwd()
    input_path = tmp_path / "requirement_input.json"
    output_path = tmp_path / "writing_task.json"
    input_path.write_text(json.dumps(_argument_brief_input(), ensure_ascii=False), encoding="utf-8")

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    task = payload["writing_task"]
    markdown_path = Path(payload["task_book_markdown_path"])

    assert payload["artifact_type"] == "writing_task"
    assert payload["quality_checks"] == {
        "required_fields_confirmed": True,
        "journal_profile_matched": True,
        "task_book_rendered": True,
    }
    assert task["topic"] == "agentic academic writing workflow"
    assert task["paper_type"] == "survey"
    assert task["language"] == "zh"
    assert task["target_journal"] == {
        "name": _journal_name(),
        "level": "CCF-B",
        "style_profile": {
            "citation_style": "GB/T 7714",
            "tone": "formal-zh",
            "structure_hint": _journal_structure_hint(),
        },
    }
    assert task["word_limit"] == {
        "total": 10000,
        "by_chapter": None,
        "chapter_allocation_stage": "paper_outline",
    }
    assert task["core_arguments"] == [
        "Contract-first requirement analysis reduces downstream drift.",
        "Explicit artifact schemas make multi-skill writing workflows auditable.",
        "Human confirmation should happen before deterministic skill execution.",
    ]
    assert task["innovation_points"] == [
        "Defines a contract-first Skill1 boundary.",
        "Separates total word confirmation from outline-stage chapter budgeting.",
        "Turns target venue requirements into machine-readable writing constraints.",
    ]
    sections = task["task_book_sections"]
    assert set(sections) == {
        "confirmation_sources_and_assumptions",
        "downstream_constraints",
        "argument_evidence_matrix",
        "target_venue_format_points",
    }
    assert {"field": "target_venue", "source": "user_confirmed"} in sections["confirmation_sources_and_assumptions"]["confirmed_sources"]
    assert any("paper_outline" in item for item in sections["confirmation_sources_and_assumptions"]["assumptions"])
    assert {item["stage"] for item in sections["downstream_constraints"]} == {
        "literature_review",
        "paper_outline",
        "draft_writing",
        "academic_formatting",
    }
    assert sections["argument_evidence_matrix"][0] == {
        "argument": "Contract-first requirement analysis reduces downstream drift.",
        "evidence_needs": ["workflow trace", "artifact diff"],
    }
    assert sections["target_venue_format_points"] == {
        "target_name": _journal_name(),
        "level": "CCF-B",
        "citation_style": "GB/T 7714",
        "tone": "formal-zh",
        "structure_hint": _journal_structure_hint(),
    }
    assert [chapter["word_budget"] for chapter in task["chapter_framework"]] == [None, None, None]
    assert task["missing_info"] == []
    assert markdown_path.exists()
    assert markdown_path.read_text(encoding="utf-8") == payload["task_book_markdown"]
    markdown = payload["task_book_markdown"]
    assert "# " in markdown and "agentic academic writing workflow" in markdown
    assert _section("confirmation_sources") in markdown
    assert _section("downstream_constraints") in markdown
    assert _section("argument_evidence_matrix") in markdown
    assert _section("target_venue_format") in markdown
    assert "paper_outline" in markdown
    assert "GB/T 7714" in markdown


def test_writing_requirement_analysis_requires_confirmed_total_word_limit(tmp_path):
    repo_root = Path.cwd()
    data = _argument_brief_input()
    del data["argument_brief"]["venue"]["word_limit"]
    input_path = tmp_path / "requirement_input.json"
    output_path = tmp_path / "writing_task.json"
    input_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "writing_task"
    assert "error" in payload
    assert "argument_brief.venue.word_limit" in payload["error"]["missing_fields"]


def test_writing_requirement_analysis_requires_reference_seed(tmp_path):
    repo_root = Path.cwd()
    data = _argument_brief_input()
    data["references_seed"] = []
    input_path = tmp_path / "requirement_input.json"
    output_path = tmp_path / "writing_task.json"
    input_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "references_seed" in payload["error"]["missing_fields"]


def test_writing_requirement_analysis_requires_specific_target_venue_name(tmp_path):
    repo_root = Path.cwd()
    data = _argument_brief_input()
    del data["argument_brief"]["venue"]["journal"]
    input_path = tmp_path / "requirement_input.json"
    output_path = tmp_path / "writing_task.json"
    input_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "argument_brief.venue.target_name" in payload["error"]["missing_fields"]


def test_writing_requirement_analysis_rejects_non_specific_target_venue(tmp_path):
    repo_root = Path.cwd()
    data = _argument_brief_input()
    data["argument_brief"]["venue"]["journal"] = _non_specific_target()
    input_path = tmp_path / "requirement_input.json"
    output_path = tmp_path / "writing_task.json"
    input_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "argument_brief.venue.target_name" in payload["error"]["missing_fields"]


def test_writing_requirement_analysis_accepts_conference_target_and_research_type(tmp_path):
    repo_root = Path.cwd()
    data = _argument_brief_input()
    venue = data["argument_brief"]["venue"]
    venue.pop("journal")
    venue["conference"] = "ACL"
    venue["paper_type"] = _research_type()
    venue["level"] = "CCF-A"
    input_path = tmp_path / "requirement_input.json"
    output_path = tmp_path / "writing_task.json"
    input_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    task = payload["writing_task"]
    assert task["paper_type"] == "research"
    assert task["target_journal"]["name"] == "ACL"
    assert task["target_journal"]["level"] == "CCF-A"


def test_writing_requirement_analysis_keeps_provenance_out_of_target_level(tmp_path):
    repo_root = Path.cwd()
    data = _argument_brief_input()
    data["argument_brief"]["venue"]["level"] = "\u63a8\u65ad\uff1a\u7528\u6237\u6700\u7ec8\u786e\u8ba4\u552f\u4e00\u76ee\u6807\u671f\u520a"
    input_path = tmp_path / "requirement_input.json"
    output_path = tmp_path / "writing_task.json"
    input_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["writing_task"]["target_journal"]["level"] == "unspecified"


def _argument_brief_input() -> dict:
    return {
        "user_request": "Prepare a Chinese academic paper writing task.",
        "argument_brief": {
            "topic": "agentic academic writing workflow",
            "problem": {
                "actor": "students and researchers writing academic papers",
                "failure_mode": "requirements, literature review, outline, and drafting drift across tools",
                "root_cause": "missing artifact contracts and deterministic skill gates",
            },
            "gap": {
                "prior_assumptions": ["A chat-only writing assistant can keep all workflow state in context."],
                "type": "structural",
            },
            "core_claim": "A contract-first skill workflow can reduce downstream writing drift.",
            "contribution_name": "contract-first Skill1",
            "core_arguments": [
                "Contract-first requirement analysis reduces downstream drift.",
                "Explicit artifact schemas make multi-skill writing workflows auditable.",
                "Human confirmation should happen before deterministic skill execution.",
            ],
            "contributions": [
                "Defines a contract-first Skill1 boundary.",
                "Separates total word confirmation from outline-stage chapter budgeting.",
                "Turns target venue requirements into machine-readable writing constraints.",
            ],
            "venue": {
                "paper_type": _survey_type(),
                "journal": _journal_name(),
                "level": "CCF-B",
                "word_limit": 10000,
                "language": "zh",
            },
            "scope": {
                "domain": "LLM agents for academic writing",
                "subtopics": ["requirement analysis", "literature review", "outline generation"],
                "boundary": "Do not evaluate plagiarism services or model pretraining.",
            },
            "section_plan": [
                {"chapter_id": "1", "title": "Introduction", "key_points": ["Background", "Problem", "Contributions"], "depends_on": None},
                {"chapter_id": "2", "title": "Related Work", "key_points": ["Research context"], "depends_on": None},
                {"chapter_id": "3", "title": "System Design", "key_points": ["Architecture", "Contracts"], "depends_on": None},
            ],
            "narrative_spine": "Contract clarity should precede literature review and drafting.",
            "evidence_plan": [
                {"argument": "Contract-first requirement analysis reduces downstream drift.", "needs": ["workflow trace", "artifact diff"]},
            ],
        },
        "references_seed": [{"id": "seed-bib", "type": "bibtex", "path": "case/references/seed.bib"}],
        "provenance": {
            "topic": "user_confirmed",
            "core_claim": "user_confirmed",
            "word_limit": "user_confirmed",
            "target_venue": "user_confirmed",
            "references_seed": "source_text",
        },
    }


def _journal_name() -> str:
    return "\u8ba1\u7b97\u673a\u7814\u7a76\u4e0e\u53d1\u5c55"


def _journal_structure_hint() -> str:
    return "\u6458\u8981(\u4e2d\u82f1)-\u5f15\u8a00-\u76f8\u5173\u5de5\u4f5c-\u65b9\u6cd5-\u5b9e\u9a8c-\u8ba8\u8bba-\u7ed3\u8bba-\u53c2\u8003\u6587\u732e"


def _survey_type() -> str:
    return "\u7efc\u8ff0"


def _research_type() -> str:
    return "\u7814\u7a76\u578b\u8bba\u6587"


def _non_specific_target() -> str:
    return "\u5f85\u5b9a\uff08\u53c2\u8003\u300a\u8ba1\u7b97\u673a\u7814\u7a76\u4e0e\u53d1\u5c55\u300b\u98ce\u683c\uff09"


def _section(name: str) -> str:
    sections = {
        "confirmation_sources": "\u786e\u8ba4\u6765\u6e90\u4e0e\u5047\u8bbe",
        "downstream_constraints": "\u540e\u7eed\u9636\u6bb5\u7ea6\u675f",
        "argument_evidence_matrix": "\u6838\u5fc3\u8bba\u70b9-\u8bc1\u636e\u9700\u6c42\u77e9\u9635",
        "target_venue_format": "\u76ee\u6807\u671f\u520a/\u4f1a\u8bae\u683c\u5f0f\u8981\u70b9",
    }
    return sections[name]
