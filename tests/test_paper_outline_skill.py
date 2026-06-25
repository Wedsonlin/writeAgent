from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_paper_outline_builds_evidence_aligned_json_and_markdown(tmp_path):
    output_path = _run_outline(tmp_path, _outline_input())
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    outline = payload["outline"]
    markdown_path = Path(payload["outline_markdown_path"])
    markdown = markdown_path.read_text(encoding="utf-8")

    assert payload["artifact_type"] == "outline"
    assert payload["outline_markdown"] == markdown
    assert markdown_path == output_path.with_suffix(".md")
    assert outline["topic"] == "大模型时代 AI Infrastructure 综述"
    assert outline["paper_type"] == "survey"
    assert outline["structure_rationale"]
    assert outline["logic_graph"]
    assert outline["argument_coverage"]
    assert outline["innovation_coverage"]
    assert outline["word_budget_plan"]

    sections = outline["sections"]
    assert any(section["level"] == 1 for section in sections)
    assert any(section["level"] == 2 for section in sections)
    assert any(section["title"] == "摘要" for section in sections)
    assert any(section["title"] == "参考文献" for section in sections)
    assert not any(section["title"] in {"实验", "实验结果", "结果"} for section in sections)

    first_body = next(section for section in sections if section["title"].startswith("引言"))
    for field in [
        "section_id",
        "rhetorical_role",
        "core_points",
        "linked_core_arguments",
        "linked_innovation_points",
        "supporting_papers",
        "evidence_notes",
        "transition_in",
        "transition_out",
    ]:
        assert field in first_body

    covered_arguments = {item["argument"] for item in outline["argument_coverage"]}
    covered_innovations = {item["innovation"] for item in outline["innovation_coverage"]}
    assert covered_arguments == set(_outline_input()["writing_task"]["core_arguments"])
    assert covered_innovations == set(_outline_input()["writing_task"]["innovation_points"])

    assert "## 论点覆盖矩阵" in markdown
    assert "## 创新点覆盖矩阵" in markdown
    assert "vllm2023" in markdown


def test_paper_outline_allocates_non_uniform_budgets_and_downgrades_weak_support(tmp_path):
    output_path = _run_outline(tmp_path, _outline_input())
    outline = json.loads(output_path.read_text(encoding="utf-8"))["outline"]

    plan = outline["word_budget_plan"]
    body_budgets = [item["word_budget"] for item in plan if item["section_id"] != "references"]
    assert sum(body_budgets) == 6000
    assert len(set(body_budgets)) > 1

    weak_argument = next(
        item for item in outline["argument_coverage"] if item["support_strength"] == "weak"
    )
    assert weak_argument["claim_mode"] == "gap_or_discussion"
    assert "研究缺口" in weak_argument["treatment"] or "讨论" in weak_argument["treatment"]
    assert weak_argument["supporting_papers"] == ["vllm2023"]


def _run_outline(tmp_path: Path, payload: dict) -> Path:
    repo_root = Path.cwd()
    input_path = tmp_path / "outline_input.json"
    output_path = tmp_path / "outline.json"
    input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "skill_packs" / "academic-paper-writing" / "skills" / "paper-outline" / "scripts" / "run.py"),
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

    assert result.returncode == 0, result.stderr
    return output_path


def _outline_input() -> dict:
    core_arguments = [
        "AI Infra 已从单点算力供给演化为跨层协同的系统工程。",
        "训练基础设施与推理基础设施正在围绕不同瓶颈显著分化。",
    ]
    innovation_points = [
        "构建面向大模型时代 AI Infra 的分层分类框架。",
        "总结 AI Infra 的综合评价指标与工程权衡。",
    ]
    return {
        "task_book_markdown": "# 论文写作任务书\n\n主题：大模型时代 AI Infrastructure 综述。",
        "literature_report_markdown": "# 文献梳理报告\n\n文献显示训练与推理基础设施已经形成分化。",
        "writing_task": {
            "topic": "大模型时代 AI Infrastructure 综述",
            "paper_type": "survey",
            "research_scope": {
                "object": "AI Infrastructure",
                "subtopics": ["训练基础设施", "推理基础设施", "RAG 基础设施"],
            },
            "word_limit": {
                "total": 6000,
                "by_chapter": None,
                "chapter_allocation_stage": "paper_outline",
            },
            "core_arguments": core_arguments,
            "innovation_points": innovation_points,
            "chapter_framework": [
                {"chapter_id": "1", "title": "引言", "key_points": ["研究背景", "问题定义"], "word_budget": None},
                {"chapter_id": "2", "title": "研究现状与领域脉络", "key_points": ["研究现状", "领域脉络"], "word_budget": None},
                {"chapter_id": "3", "title": "训练与推理基础设施比较", "key_points": ["训练侧瓶颈", "推理侧瓶颈"], "word_budget": None},
                {"chapter_id": "4", "title": "研究缺口与未来趋势", "key_points": ["研究缺口", "未来趋势"], "word_budget": None},
            ],
            "task_book_sections": {
                "argument_evidence_matrix": [
                    {"argument": core_arguments[0], "needs": ["系统分层文献", "基础设施案例"]},
                    {"argument": core_arguments[1], "needs": ["训练系统文献", "推理服务文献"]},
                ]
            },
        },
        "literature_report": {
            "papers": [
                {"id": "zero2020", "title": "ZeRO", "evidence_strength": "moderate"},
                {"id": "vllm2023", "title": "vLLM", "evidence_strength": "moderate"},
            ],
            "research_landscape": {
                "clusters": [
                    {"name": "训练基础设施", "paper_ids": ["zero2020"]},
                    {"name": "推理服务", "paper_ids": ["vllm2023"]},
                ]
            },
            "argument_support_matrix": [
                {
                    "argument": core_arguments[0],
                    "supporting_papers": ["zero2020", "vllm2023"],
                    "support_strength": "moderate",
                    "evidence_summaries": ["ZeRO 与 vLLM 分别说明训练和推理基础设施的系统化优化。"],
                    "gap": "",
                },
                {
                    "argument": core_arguments[1],
                    "supporting_papers": ["vllm2023"],
                    "support_strength": "weak",
                    "evidence_summaries": ["vLLM 可说明推理侧 KV Cache 瓶颈，但训练侧对照仍不足。"],
                    "gap": "缺少训练侧与推理侧统一对比文献。",
                },
            ],
            "innovation_support_matrix": [
                {
                    "innovation": innovation_points[0],
                    "supporting_papers": ["zero2020", "vllm2023"],
                    "support_strength": "moderate",
                    "evidence_summaries": ["两篇文献可支撑分层分类框架。"],
                    "gap": "",
                },
                {
                    "innovation": innovation_points[1],
                    "supporting_papers": ["vllm2023"],
                    "support_strength": "weak",
                    "evidence_summaries": ["现有文献覆盖吞吐与显存，成本和能耗指标仍不足。"],
                    "gap": "缺少综合评价指标文献。",
                },
            ],
            "research_gaps": ["缺少覆盖训练、推理、成本和能耗的统一评价框架。"],
        },
    }
