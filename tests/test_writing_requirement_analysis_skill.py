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
    assert task["topic"] == "面向学术论文写作的智能 Agent 设计与实现"
    assert task["paper_type"] == "system"
    assert task["language"] == "zh"
    assert task["target_journal"] == {
        "name": "计算机研究与发展",
        "level": "CCF-B",
        "style_profile": {
            "citation_style": "GB/T 7714",
            "tone": "formal-zh",
            "structure_hint": "摘要(中英)-引言-相关工作-方法-实验-讨论-结论-参考文献",
        },
    }
    assert task["word_limit"] == {
        "total": 10000,
        "by_chapter": None,
        "chapter_allocation_stage": "paper_outline",
    }
    assert task["core_arguments"] == [
        "大脑决策 + Skill 工具调用模式可显著降低学术写作门槛",
        "统一输入输出字段是多 Skill 协作的关键保障",
        "LangGraph 与 OpenClaw 双轨编排可兼顾本地开发与平台部署",
    ]
    assert task["innovation_points"] == [
        "提出 LangGraph 编排 + OpenClaw 兼容 Skill 的双轨架构",
        "以 JSON Schema 作为跨 Skill 契约的统一基线",
        "针对论文写作场景设计了 6 个层次清晰的 Skill 划分",
    ]
    assert [chapter["word_budget"] for chapter in task["chapter_framework"]] == [None, None, None]
    assert task["missing_info"] == []
    assert markdown_path.exists()
    assert markdown_path.read_text(encoding="utf-8") == payload["task_book_markdown"]
    assert "# 论文写作任务书 · 面向学术论文写作的智能 Agent 设计与实现" in payload["task_book_markdown"]
    assert "- 总字数：10000" in payload["task_book_markdown"]
    assert "- 章节字数分配：由 `paper_outline` 阶段完成" in payload["task_book_markdown"]


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


def _argument_brief_input() -> dict:
    return {
        "user_request": "高级人工智能课程论文写作 Agent 与 Skill 设计作业。",
        "argument_brief": {
            "topic": "面向学术论文写作的智能 Agent 设计与实现",
            "problem": {
                "actor": "需要完成课程论文或科研写作的学生与研究者",
                "failure_mode": "多阶段写作工作流缺少可追踪的结构化状态。",
                "root_cause": "缺少统一 artifact 契约和可复用 Skill 工作流。",
            },
            "gap": {
                "prior_assumptions": ["通用写作助手可以长期保持所有阶段上下文。"],
                "type": "structural",
            },
            "core_claim": "本文表明，大脑决策与 Skill 工具调用结合的架构可以降低学术论文写作门槛。",
            "contribution_name": "双轨 Skill 架构",
            "core_arguments": [
                "大脑决策 + Skill 工具调用模式可显著降低学术写作门槛",
                "统一输入输出字段是多 Skill 协作的关键保障",
                "LangGraph 与 OpenClaw 双轨编排可兼顾本地开发与平台部署",
            ],
            "contributions": [
                "提出 LangGraph 编排 + OpenClaw 兼容 Skill 的双轨架构",
                "以 JSON Schema 作为跨 Skill 契约的统一基线",
                "针对论文写作场景设计了 6 个层次清晰的 Skill 划分",
            ],
            "venue": {
                "paper_type": "system",
                "journal": "计算机研究与发展",
                "level": "CCF-B",
                "word_limit": 10000,
                "language": "zh",
            },
            "scope": {
                "domain": "大语言模型 Agent · 学术写作辅助 · 工具编排",
                "subtopics": ["需求结构化与选题定位", "文献梳理与引用规范", "大纲生成与正文撰写"],
                "boundary": "不讨论模型本身的预训练与微调；不评测查重服务",
            },
            "section_plan": [
                {"chapter_id": "1", "title": "引言", "key_points": ["背景", "问题", "本文贡献"], "depends_on": None},
                {"chapter_id": "2", "title": "相关工作", "key_points": ["研究脉络"], "depends_on": None},
                {"chapter_id": "3", "title": "系统设计", "key_points": ["总体架构", "核心模块"], "depends_on": None},
            ],
            "narrative_spine": "需求结构化、文献梳理和正文生成需要统一契约承接。",
            "evidence_plan": [],
        },
        "references_seed": [{"id": "seed-bib", "type": "bibtex", "path": "case/references/seed.bib"}],
        "provenance": {
            "core_claim": "用户确认",
            "word_limit": "用户确认",
            "references_seed": "原文/已有数据",
        },
    }
