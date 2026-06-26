from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path


SKILLS = Path("skill_packs") / "academic-paper-writing" / "skills"


def test_core_stage_scripts_emit_formal_artifacts(tmp_path):
    repo = Path.cwd()

    stage1 = _run_skill(
        repo,
        "writing-requirement-analysis",
        SKILLS / "writing-requirement-analysis" / "assets" / "input.example.json",
        tmp_path / "artifacts" / "01-论文写作任务书.json",
    )
    assert stage1["artifact_type"] == "writing_task"
    assert Path(stage1["task_book_markdown_path"]).name == "01-论文写作任务书.md"

    literature_input = tmp_path / "tmp" / "stage2-input.json"
    literature_input.parent.mkdir(parents=True, exist_ok=True)
    literature_input.write_text(json.dumps(_literature_input(repo, tmp_path), ensure_ascii=False), encoding="utf-8")
    stage2 = _run_skill(
        repo,
        "literature-review",
        literature_input,
        tmp_path / "artifacts" / "02-文献处理报告.json",
    )
    assert stage2["artifact_type"] == "literature_report"
    assert Path(stage2["literature_report_markdown_path"]).name == "02-文献处理报告.md"
    assert stage2["literature_report"]["papers"]

    outline_input = tmp_path / "tmp" / "stage3-input.json"
    outline_input.parent.mkdir(parents=True, exist_ok=True)
    outline_input.write_text(json.dumps(_outline_input(), ensure_ascii=False), encoding="utf-8")
    stage3 = _run_skill(repo, "paper-outline", outline_input, tmp_path / "artifacts" / "03-论文详细大纲.json")
    assert stage3["artifact_type"] == "outline"
    assert Path(stage3["outline_markdown_path"]).name == "03-论文详细大纲.md"
    assert stage3["outline"]["sections"]

    content_input = tmp_path / "tmp" / "stage4-input.json"
    content_input.write_text(json.dumps(_content_input(), ensure_ascii=False), encoding="utf-8")
    stage4 = _run_skill(repo, "paper-content-generation", content_input, tmp_path / "artifacts" / "04-分章节初稿.json")
    assert stage4["artifact_type"] == "draft"
    assert Path(stage4["draft"]["draft_markdown_path"]).name == "04-分章节初稿.md"
    assert stage4["draft"]["quality_checks"]["citations_valid"] is True

    stage5 = _run_skill(
        repo,
        "academic-formatting",
        SKILLS / "academic-formatting" / "assets" / "draft.sample.json",
        tmp_path / "artifacts" / "05-格式规范的论文终稿.json",
    )
    formatted = stage5["formatted_draft"]
    assert stage5["artifact_type"] == "formatted_draft"
    assert Path(formatted["markdown_path"]).name == "05-格式规范的论文终稿.md"
    assert Path(formatted["docx_path"]).name == "05-格式规范的论文终稿.docx"
    assert zipfile.is_zipfile(formatted["docx_path"])

    stage6 = _run_skill(
        repo,
        "polish-and-plagiarism",
        SKILLS / "polish-and-plagiarism" / "assets" / "polished.sample.json",
        tmp_path / "artifacts" / "06-润色论文终稿.json",
    )
    polished = stage6["polished_draft"]
    assert stage6["artifact_type"] == "polished_draft"
    assert polished["quality_checks"]["tone_academic"] is True
    assert polished["quality_checks"]["docx_exported"] is True
    assert Path(polished["markdown_path"]).name == "06-润色论文终稿.md"
    assert Path(polished["docx_path"]).name == "06-润色论文终稿.docx"


def test_content_generation_keeps_validator_boundary_and_citation_diagnostics(tmp_path):
    repo = Path.cwd()
    payload = _content_input()
    content_input = tmp_path / "input.json"
    output_path = tmp_path / "draft.json"

    missing_draft = dict(payload)
    missing_draft.pop("draft")
    content_input.write_text(json.dumps(missing_draft, ensure_ascii=False), encoding="utf-8")
    error_payload = _run_skill(repo, "paper-content-generation", content_input, output_path, expect_success=False)
    assert error_payload["error"]["fields"] == ["draft"]

    bad_citation = _content_input()
    bad_citation["draft"]["sections"][0]["citations_used"] = ["vllm2023"]
    bad_citation["draft"]["sections"][0]["evidence_used"] = [{"paper_id": "vllm2023", "summary": "vLLM evidence"}]
    content_input.write_text(json.dumps(bad_citation, ensure_ascii=False), encoding="utf-8")
    error_payload = _run_skill(repo, "paper-content-generation", content_input, output_path, expect_success=False)
    assert "draft.sections[0].content_markdown.citation_marker" in error_payload["error"]["fields"]
    assert error_payload["error"]["details"]["citation_mismatches"][0]["expected_marker"] == 2


def test_polish_script_requires_agent_polished_markdown(tmp_path):
    repo = Path.cwd()
    example = json.loads((repo / SKILLS / "polish-and-plagiarism" / "assets" / "polished.sample.json").read_text(encoding="utf-8"))
    example.pop("polished_markdown")
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(example, ensure_ascii=False), encoding="utf-8")

    payload = _run_skill(repo, "polish-and-plagiarism", input_path, tmp_path / "06-润色论文终稿.json", expect_success=False)

    assert payload["artifact_type"] == "polished_draft"
    assert "polished_markdown" in payload["error"]["fields"]


def _run_skill(
    repo: Path,
    skill: str,
    input_path: Path,
    output_path: Path,
    *,
    expect_success: bool = True,
) -> dict:
    script = repo / SKILLS / skill / "scripts" / "run.py"
    result = subprocess.run(
        [sys.executable, str(script), "--input", str(input_path), "--output", str(output_path)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_success:
        assert result.returncode == 0, result.stderr or output_path.read_text(encoding="utf-8")
    else:
        assert result.returncode == 1
    return json.loads(output_path.read_text(encoding="utf-8"))


def _outline_input() -> dict:
    argument = "AI Infra has evolved from isolated compute supply to cross-layer system engineering."
    innovation = "Build a layered taxonomy for large-model AI infrastructure."
    return {
        "writing_task": {
            "topic": "Large-model AI infrastructure",
            "paper_type": "survey",
            "word_limit": {"total": 3200},
            "core_arguments": [argument],
            "innovation_points": [innovation],
            "chapter_framework": [
                {"chapter_id": "1", "title": "Introduction", "key_points": ["background", "problem"]},
                {"chapter_id": "2", "title": "Training and inference infrastructure", "key_points": ["training", "serving"]},
                {"chapter_id": "3", "title": "Future challenges", "key_points": ["cost", "energy"]},
            ],
        },
        "literature_report": {
            "papers": [
                {"id": "zero2020", "title": "ZeRO", "evidence_strength": "moderate"},
                {"id": "vllm2023", "title": "vLLM", "evidence_strength": "moderate"},
            ],
            "argument_support_matrix": [
                {
                    "argument": argument,
                    "supporting_papers": ["zero2020", "vllm2023"],
                    "support_strength": "moderate",
                    "evidence_summaries": ["ZeRO and vLLM show cross-layer system optimization."],
                    "gap": "",
                }
            ],
            "innovation_support_matrix": [
                {
                    "innovation": innovation,
                    "supporting_papers": ["zero2020", "vllm2023"],
                    "support_strength": "moderate",
                    "evidence_summaries": ["The papers support a taxonomy spanning training and inference."],
                    "gap": "",
                }
            ],
        },
    }


def _literature_input(repo: Path, tmp_path: Path) -> dict:
    payload = json.loads((repo / SKILLS / "literature-review" / "assets" / "input.example.json").read_text(encoding="utf-8"))
    bib_path = tmp_path / "tmp" / "seed.bib"
    bib_path.parent.mkdir(parents=True, exist_ok=True)
    bib_path.write_text(
        """@misc{yao2022react,
  author = {Yao, Shunyu and Zhao, Jeffrey and Yu, Dian},
  title = {ReAct: Synergizing Reasoning and Acting in Language Models},
  year = {2022},
  eprint = {2210.03629},
  archivePrefix = {arXiv}
}
""",
        encoding="utf-8",
    )
    payload["writing_task"]["references_seed"] = [
        {
            "id": "seed-bib",
            "type": "bibtex",
            "path": str(bib_path),
        }
    ]
    return payload


def _content_input() -> dict:
    argument = "AI Infra has evolved from isolated compute supply to cross-layer system engineering."
    innovation = "Build a layered taxonomy for large-model AI infrastructure."
    sections = [
        _section("1", "Introduction", argument, innovation, "zero2020"),
        _section("2", "Training infrastructure", argument, innovation, "zero2020"),
        _section("3", "Inference infrastructure", argument, innovation, "vllm2023"),
        _section("4", "Operations and governance", argument, innovation, "vllm2023", support_status="weak"),
        _section("5", "Conclusion", argument, innovation, "zero2020"),
    ]
    return {
        "outline_markdown": "# Outline\n",
        "literature_report_markdown": "# Literature\n",
        "writing_task": {
            "topic": "Large-model AI infrastructure",
            "paper_type": "survey",
            "core_arguments": [argument],
            "innovation_points": [innovation],
        },
        "outline": {
            "sections": [{"section_id": str(i), "title": s["title"], "level": 1, "word_budget": 420} for i, s in enumerate(sections, 1)],
            "argument_coverage": [{"argument": argument, "section_ids": ["1", "2", "3", "4", "5"]}],
            "innovation_coverage": [{"innovation": innovation, "section_ids": ["1", "2", "3", "4", "5"]}],
        },
        "literature_report": {
            "paper_reading_cards": [
                {"paper_id": "zero2020", "reading_status": "read", "source_urls": ["https://example.com/zero"]},
                {"paper_id": "vllm2023", "reading_status": "read", "source_urls": ["https://example.com/vllm"]},
            ],
            "argument_support_matrix": [
                {"argument": argument, "supporting_papers": ["zero2020", "vllm2023"], "support_strength": "moderate"}
            ],
            "innovation_support_matrix": [
                {"innovation": innovation, "supporting_papers": ["zero2020", "vllm2023"], "support_strength": "moderate"}
            ],
            "references": [
                {"id": "zero2020", "title": "ZeRO", "gb7714": "Rajbhandari S, et al. ZeRO[C]. 2020."},
                {"id": "vllm2023", "title": "vLLM", "gb7714": "Kwon W, et al. vLLM[C]. 2023."},
            ],
        },
        "draft": {
            "title": "Large-model AI infrastructure",
            "abstract": _section_text("This survey frames large-model AI infrastructure as a cross-layer system problem.", "[1]"),
            "keywords": ["AI Infra", "large models", "distributed training", "inference serving"],
            "sections": sections,
            "references": [
                {"id": "zero2020", "title": "ZeRO", "gb7714": "Rajbhandari S, et al. ZeRO[C]. 2020."},
                {"id": "vllm2023", "title": "vLLM", "gb7714": "Kwon W, et al. vLLM[C]. 2023."},
            ],
            "argument_trace": [{"argument": argument, "section_ids": ["1", "2", "3", "4", "5"], "support_status": "moderate"}],
            "innovation_trace": [{"innovation": innovation, "section_ids": ["1", "2", "3", "4", "5"], "support_status": "moderate"}],
            "unsupported_claims": ["Comparable energy and cost metrics still require more cross-platform data."],
            "open_questions": ["How can heterogeneous accelerators be evaluated under a unified cost model?"],
        },
    }


def _section(section_id: str, title: str, argument: str, innovation: str, paper_id: str, *, support_status: str = "moderate") -> dict:
    marker = "[1]" if paper_id == "zero2020" else "[2]"
    return {
        "id": section_id,
        "source_outline_section_id": section_id,
        "title": title,
        "level": 1,
        "target_word_count": 420,
        "content_markdown": _section_text(f"{title} analyzes the architecture and scheduling mechanism of AI infrastructure.", marker),
        "citations_used": [paper_id],
        "linked_core_arguments": [argument],
        "linked_innovation_points": [innovation],
        "evidence_used": [{"paper_id": paper_id, "summary": "The cited paper provides system evidence."}],
        "data_used": [],
        "transition_in": "This section continues the previous system framing.",
        "transition_out": "The next section compares another layer of the infrastructure stack.",
        "support_status": support_status,
        "section_depth_checks": {
            "problem_framed": True,
            "mechanism_explained": True,
            "evidence_interpreted": True,
            "comparison_or_tradeoff": True,
            "limitation_or_boundary": True,
            "argument_return": True,
        },
    }


def _section_text(seed: str, marker: str) -> str:
    sentences = [
        f"{seed} The problem is not only raw compute supply but also the coordination of memory, communication, runtime scheduling, and service isolation {marker}. ",
        "The mechanism works through layered resource control, cache management, parallel execution, and feedback from observable system metrics. ",
        "Prior evidence and paper results show that memory partitioning, request batching, and compiler optimization can shift the bottleneck across layers. ",
        "Compared with a single accelerator benchmark, this tradeoff view explains why throughput, latency, cost, and reliability must be analyzed together. ",
        "The limitation is that cost and energy data are often platform-specific, so the boundary of the claim should remain explicit. ",
        "Therefore, the section returns to the main argument: AI Infra should be evaluated as a cross-layer system rather than a single component. ",
        "This also supports the innovation because a layered taxonomy gives each representative system a clear position in the survey. ",
        "Future work still needs unified measurement for heterogeneous clusters and multi-tenant inference workloads. ",
    ]
    return "".join(sentences * 4)
