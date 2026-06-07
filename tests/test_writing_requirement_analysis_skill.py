from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_writing_requirement_analysis_builds_writing_task_from_argument_brief(tmp_path):
    repo_root = Path.cwd()
    golden = json.loads((repo_root / "case" / "01-论文写作任务书.json").read_text(encoding="utf-8"))
    input_path = tmp_path / "requirement_input.json"
    output_path = tmp_path / "writing_task.json"
    input_path.write_text(json.dumps(_argument_brief_input(golden), ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
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

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    task = payload["writing_task"]
    assert payload["artifact_type"] == "writing_task"
    assert task["topic"] == golden["topic"]
    assert task["paper_type"] == "system"
    assert task["target_journal"] == golden["target_journal"]
    assert task["core_arguments"] == golden["core_arguments"]
    assert task["innovation_points"] == golden["innovation_points"]
    assert len(task["chapter_framework"]) == 8
    assert task["chapter_framework"][0]["title"] == "引言"
    assert task["references_seed"] == golden["references_seed"]
    assert task["missing_info"] == golden["missing_info"]


def _argument_brief_input(golden: dict) -> dict:
    return {
        "user_request": "高级人工智能课程论文写作 Agent 与 Skill 设计作业。",
        "argument_brief": {
            "topic": golden["topic"],
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
            "core_arguments": golden["core_arguments"],
            "contributions": golden["innovation_points"],
            "venue": {
                "paper_type": golden["paper_type"],
                "journal": golden["target_journal"]["name"],
                "level": golden["target_journal"]["level"],
                "word_limit": golden["word_limit"]["total"],
                "language": golden["language"],
            },
            "scope": golden["research_scope"],
            "section_plan": golden["chapter_framework"],
            "narrative_spine": "需求结构化、文献梳理和正文生成需要统一契约承接。",
            "evidence_plan": [],
        },
        "references_seed": golden["references_seed"],
        "provenance": {
            "core_claim": "用户确认",
            "word_limit": "原文/已有数据",
            "references_seed": "原文/已有数据",
        },
    }
