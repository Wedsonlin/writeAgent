from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_paper_outline_allocates_chapter_word_budgets_when_skill1_leaves_them_open(tmp_path):
    repo_root = Path.cwd()
    input_path = tmp_path / "outline_input.json"
    output_path = tmp_path / "outline.json"
    input_path.write_text(json.dumps(_outline_input(), ensure_ascii=False), encoding="utf-8")

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
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    sections = payload["outline"]["sections"]

    assert payload["artifact_type"] == "outline"
    assert payload["outline"]["total_word_budget"] == 10000
    assert [section["word_budget"] for section in sections] == [2500, 2500, 2500, 2500]


def _outline_input() -> dict:
    return {
        "writing_task": {
            "word_limit": {
                "total": 10000,
                "by_chapter": None,
                "chapter_allocation_stage": "paper_outline",
            },
            "chapter_framework": [
                {"chapter_id": "1", "title": "引言", "key_points": ["背景"], "word_budget": None, "depends_on": None},
                {"chapter_id": "2", "title": "相关工作", "key_points": ["脉络"], "word_budget": None, "depends_on": None},
                {"chapter_id": "3", "title": "系统设计", "key_points": ["架构"], "word_budget": None, "depends_on": None},
                {"chapter_id": "4", "title": "结论", "key_points": ["总结"], "word_budget": None, "depends_on": None},
            ],
        },
        "literature_report": {"papers": [], "research_landscape": {"clusters": []}},
    }
