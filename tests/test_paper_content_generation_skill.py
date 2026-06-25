from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_content_generation_outputs_traceable_json_and_markdown(tmp_path):
    output_path = _run_content(tmp_path, _content_input())
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    draft = payload["draft"]
    markdown_path = Path(draft["draft_markdown_path"])
    markdown = markdown_path.read_text(encoding="utf-8")

    assert payload["artifact_type"] == "draft"
    assert markdown_path == output_path.with_suffix(".md")
    assert draft["draft_markdown"] == markdown
    assert "# 大模型时代 AI Infrastructure 综述" in markdown
    assert "## 摘要" in markdown
    assert "## 参考文献" in markdown

    assert draft["quality_checks"]["outline_sections_covered"] is True
    assert draft["quality_checks"]["citations_valid"] is True
    assert draft["quality_checks"]["argument_trace_present"] is True
    assert draft["quality_checks"]["innovation_trace_present"] is True
    assert draft["quality_checks"]["markdown_sidecar_written"] is True

    section = draft["sections"][0]
    assert section["source_outline_section_id"] == "1"
    assert section["target_word_count"] == 420
    assert section["linked_core_arguments"] == ["AI Infra 已从单点算力供给演化为跨层协同的系统工程。"]
    assert section["linked_innovation_points"] == ["构建面向大模型时代 AI Infra 的分层分类框架。"]
    assert section["evidence_used"][0]["paper_id"] == "zero2020"
    assert section["support_status"] == "moderate"
    assert section["citations_used"] == ["zero2020"]
    assert draft["argument_trace"][0]["argument"].startswith("AI Infra")
    assert draft["innovation_trace"][0]["innovation"].startswith("构建面向")


def test_content_generation_rejects_unknown_citation_ids(tmp_path):
    payload = _content_input()
    payload["draft"]["sections"][0]["citations_used"] = ["missing2024"]

    output_path = _run_content(tmp_path, payload, expect_success=False)
    error = json.loads(output_path.read_text(encoding="utf-8"))["error"]

    assert "draft.sections[0].citations_used" in error["fields"]


def test_content_generation_accepts_numeric_range_citations(tmp_path):
    payload = _content_input()
    section = payload["draft"]["sections"][0]
    section["content_markdown"] = _section_text(
        "引言部分综合训练系统与推理系统证据说明 AI Infra 的跨层协同特征。",
        "[1-2]",
    )
    section["citations_used"] = ["1", "2"]

    output_path = _run_content(tmp_path, payload)
    draft = json.loads(output_path.read_text(encoding="utf-8"))["draft"]

    assert draft["sections"][0]["citations_used"] == ["1", "2"]
    assert draft["quality_checks"]["citations_valid"] is True


def test_content_generation_rejects_strong_section_without_evidence_or_claim_record(tmp_path):
    payload = _content_input()
    payload["draft"]["sections"][0]["support_status"] = "strong"
    payload["draft"]["sections"][0]["citations_used"] = []
    payload["draft"]["sections"][0]["evidence_used"] = []
    payload["draft"]["unsupported_claims"] = []

    output_path = _run_content(tmp_path, payload, expect_success=False)
    error = json.loads(output_path.read_text(encoding="utf-8"))["error"]

    assert "draft.sections[0].support_status" in error["fields"]


def test_content_generation_rejects_empirical_results_without_research_data(tmp_path):
    payload = _content_input()
    payload["writing_task"]["paper_type"] = "empirical"
    payload["draft"]["sections"][1]["title"] = "实验结果"
    payload["draft"]["sections"][1]["content_markdown"] = _section_text("实验结果显示系统吞吐率显著提升，延迟明显下降。", "[1]")
    payload["research_data"] = []

    output_path = _run_content(tmp_path, payload, expect_success=False)
    error = json.loads(output_path.read_text(encoding="utf-8"))["error"]

    assert "research_data" in error["fields"]


def test_content_generation_rejects_repetitive_template_prose(tmp_path):
    payload = _content_input()
    payload["draft"]["sections"][2]["content_markdown"] = "该章节围绕大模型基础设施展开讨论。" * 90

    output_path = _run_content(tmp_path, payload, expect_success=False)
    error = json.loads(output_path.read_text(encoding="utf-8"))["error"]

    assert "draft.sections[2].content_markdown.repetitive" in error["fields"]


def test_content_generation_rejects_section_without_argument_depth_checks(tmp_path):
    payload = _content_input()
    payload["draft"]["sections"][0].pop("section_depth_checks")

    output_path = _run_content(tmp_path, payload, expect_success=False)
    error = json.loads(output_path.read_text(encoding="utf-8"))["error"]

    assert "draft.sections[0].section_depth_checks" in error["fields"]


def _run_content(tmp_path: Path, payload: dict, *, expect_success: bool = True) -> Path:
    repo_root = Path.cwd()
    input_path = tmp_path / "content_input.json"
    output_path = tmp_path / "draft.json"
    input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(
                repo_root
                / "skill_packs"
                / "academic-paper-writing"
                / "skills"
                / "paper-content-generation"
                / "scripts"
                / "run.py"
            ),
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

    if expect_success:
        assert result.returncode == 0, result.stderr or output_path.read_text(encoding="utf-8")
    else:
        assert result.returncode == 1
    return output_path


def _content_input() -> dict:
    core_argument = "AI Infra 已从单点算力供给演化为跨层协同的系统工程。"
    innovation = "构建面向大模型时代 AI Infra 的分层分类框架。"
    sections = [
        _section("1", "引言", core_argument, innovation, "zero2020"),
        _section("2", "研究现状", core_argument, innovation, "vllm2023"),
        _section("3", "训练与推理基础设施", core_argument, innovation, "zero2020"),
        _section("4", "挑战与趋势", core_argument, innovation, "vllm2023", support_status="weak"),
        _section("5", "结论", core_argument, innovation, "zero2020"),
    ]
    return {
        "outline_markdown": "# 论文大纲\n\n## 引言\n\n## 研究现状\n",
        "literature_report_markdown": "# 文献梳理报告\n\nZeRO 与 vLLM 支撑训练和推理基础设施分析。\n",
        "writing_task": {
            "topic": "大模型时代 AI Infrastructure 综述",
            "paper_type": "survey",
            "core_arguments": [core_argument],
            "innovation_points": [innovation],
        },
        "outline": {
            "sections": [
                {"section_id": "1", "title": "引言", "level": 1, "word_budget": 420},
                {"section_id": "2", "title": "研究现状", "level": 1, "word_budget": 460},
                {"section_id": "3", "title": "训练与推理基础设施", "level": 1, "word_budget": 520},
                {"section_id": "4", "title": "挑战与趋势", "level": 1, "word_budget": 430},
                {"section_id": "5", "title": "结论", "level": 1, "word_budget": 280},
            ],
            "argument_coverage": [{"argument": core_argument, "section_ids": ["1", "2", "3", "4", "5"]}],
            "innovation_coverage": [{"innovation": innovation, "section_ids": ["1", "3", "4", "5"]}],
        },
        "literature_report": {
            "paper_reading_cards": [
                {
                    "paper_id": "zero2020",
                    "reading_status": "read",
                    "main_claims_zh": ["ZeRO 通过状态分片降低大模型训练显存压力。"],
                    "source_urls": ["https://arxiv.org/abs/1910.02054"],
                    "source_artifact_ids": ["search-evidence-zero"],
                },
                {
                    "paper_id": "vllm2023",
                    "reading_status": "read",
                    "main_claims_zh": ["vLLM 通过 PagedAttention 改善推理服务吞吐。"],
                    "source_urls": ["https://arxiv.org/abs/2309.06180"],
                    "source_artifact_ids": ["search-evidence-vllm"],
                },
            ],
            "argument_support_matrix": [
                {
                    "argument": core_argument,
                    "supporting_papers": ["zero2020", "vllm2023"],
                    "support_strength": "moderate",
                    "evidence_summary": "训练与推理系统共同说明 AI Infra 的跨层协同特征。",
                }
            ],
            "innovation_support_matrix": [
                {
                    "innovation": innovation,
                    "supporting_papers": ["zero2020", "vllm2023"],
                    "support_strength": "moderate",
                    "evidence_summary": "两类系统可支撑分层分类框架。",
                }
            ],
            "research_gaps": ["统一评价框架仍不足。"],
            "references": [
                {"id": "zero2020", "title": "ZeRO", "gb7714": "Rajbhandari S, et al. ZeRO[C]. 2020."},
                {"id": "vllm2023", "title": "vLLM", "gb7714": "Kwon W, et al. vLLM[C]. 2023."},
            ],
        },
        "draft": {
            "title": "大模型时代 AI Infrastructure 综述",
            "abstract": _section_text("本文围绕大模型时代 AI Infrastructure 的系统演化展开综述。", "[1]"),
            "keywords": ["AI Infrastructure", "大模型", "分布式训练", "推理服务"],
            "sections": sections,
            "references": [
                {"id": "zero2020", "title": "ZeRO", "gb7714": "Rajbhandari S, et al. ZeRO[C]. 2020."},
                {"id": "vllm2023", "title": "vLLM", "gb7714": "Kwon W, et al. vLLM[C]. 2023."},
            ],
            "argument_trace": [{"argument": core_argument, "section_ids": ["1", "2", "3", "4", "5"], "support_status": "moderate"}],
            "innovation_trace": [{"innovation": innovation, "section_ids": ["1", "3", "4", "5"], "support_status": "moderate"}],
            "unsupported_claims": ["成本与能耗指标仍缺少统一实证数据，只能作为趋势问题讨论。"],
            "open_questions": ["需要补充跨平台成本与能耗的可比数据。"],
        },
    }


def _section(section_id: str, title: str, argument: str, innovation: str, paper_id: str, *, support_status: str = "moderate") -> dict:
    citation = "[1]" if paper_id == "zero2020" else "[2]"
    return {
        "id": section_id,
        "source_outline_section_id": section_id,
        "title": title,
        "level": 1,
        "target_word_count": 420,
        "content_markdown": _section_text(f"{title}部分说明大模型基础设施的系统化演进。", citation),
        "citations_used": [paper_id],
        "linked_core_arguments": [argument],
        "linked_innovation_points": [innovation],
        "evidence_used": [{"paper_id": paper_id, "summary": "该文献提供系统设计证据。"}],
        "data_used": [],
        "transition_in": "承接上一节的概念界定。",
        "transition_out": "转入下一节的主题比较。",
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


def _section_text(seed: str, citation: str) -> str:
    sentences = [
        f"{seed} 相关文献表明，训练系统、推理服务、调度编排和数据基础设施之间存在持续增强的耦合关系{citation}。",
        "这一变化使论文不能停留在芯片性能或单一框架比较，而需要从跨层协同的角度解释基础设施演化。",
        "在训练侧，参数状态、显存分配、通信拓扑和任务调度共同决定大模型能否稳定扩展。",
        "在推理侧，KV Cache、批处理策略、请求调度和服务隔离决定吞吐率、延迟与单位成本之间的平衡。",
        "因此，正文需要把硬件资源、软件运行时和平台治理放在同一分析框架中，而不是只讨论单点算力指标。",
        "这种写法也能为后文比较开源系统与云平台方案提供统一尺度。",
        "从研究贡献看，分层分类框架能够把代表性系统放入可解释的位置，避免文献罗列式综述。",
        "从研究限制看，成本、能耗和可靠性指标仍需要更多跨平台数据支撑，本文仅作趋势性讨论。",
    ]
    return "".join(sentences * 2)
