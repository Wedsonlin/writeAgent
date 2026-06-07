from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_literature_review_builds_report_from_source_map_and_bibtex(tmp_path):
    repo_root = Path.cwd()
    writing_task = json.loads((repo_root / "case" / "01-论文写作任务书.json").read_text(encoding="utf-8"))
    golden = json.loads((repo_root / "case" / "02-文献梳理报告.json").read_text(encoding="utf-8"))
    input_path = tmp_path / "literature_input.json"
    output_path = tmp_path / "literature_report.json"
    input_path.write_text(json.dumps(_literature_input(writing_task, golden), ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "skill_packs" / "academic-paper-writing" / "skills" / "literature-review" / "scripts" / "run.py"),
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
    report = payload["literature_report"]
    assert payload["artifact_type"] == "literature_report"
    assert [paper["id"] for paper in report["papers"]] == [paper["id"] for paper in golden["papers"]]
    assert len(report["papers"]) == len(golden["papers"])
    assert len(report["papers"]) >= 15
    assert len(report["research_landscape"]["clusters"]) == 4
    assert report["research_landscape"]["clusters"] == golden["research_landscape"]["clusters"]
    assert report["consensus"] == golden["consensus"]
    assert report["controversies"] == golden["controversies"]
    assert report["research_gaps"] == golden["research_gaps"]
    assert len(report["formatted_bibliography"]["gb7714"]) == len(report["papers"])
    assert len(report["formatted_bibliography"]["apa"]) == len(report["papers"])
    assert "unmapped_papers" not in report


def _literature_input(writing_task: dict, golden: dict) -> dict:
    return {
        "writing_task": writing_task,
        "citation_style": golden["citation_style"],
        "source_map": [
            {
                "paper_id": paper["id"],
                "research_question": paper["title"],
                "core_method": paper.get("abstract", ""),
                "main_finding": paper["key_claims"][0] if paper.get("key_claims") else "",
                "key_claims": paper.get("key_claims", []),
                "evidence_strength": paper.get("evidence_strength", "weak"),
                "limitations": [],
                "alignment_to_core": paper.get("alignment_to_core", []),
                "provenance": {"main_finding": "abstract"},
            }
            for paper in golden["papers"]
        ],
        "landscape": {
            "keywords": golden["keywords"],
            "clusters": golden["research_landscape"]["clusters"],
            "consensus": golden["consensus"],
            "controversies": golden["controversies"],
            "research_gaps": golden["research_gaps"],
            "timeline_summary": golden["research_landscape"]["timeline_summary"],
        },
        "extra_references": [],
    }
