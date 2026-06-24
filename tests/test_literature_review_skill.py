from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_literature_review_builds_report_from_asset_input(tmp_path):
    repo_root = Path.cwd()
    assets = repo_root / "skill_packs" / "academic-paper-writing" / "skills" / "literature-review" / "assets"
    source = json.loads((assets / "input.example.json").read_text(encoding="utf-8"))
    bib_path = tmp_path / "seed.bib"
    bib_path.write_text(
        """@misc{yao2022react,
  author = {Yao, Shunyu and Zhao, Jeffrey and Yu, Dian and Du, Nan and Shafran, Izhak and Narasimhan, Karthik and Cao, Yuan},
  title = {ReAct: Synergizing Reasoning and Acting in Language Models},
  year = {2022},
  eprint = {2210.03629},
  archivePrefix = {arXiv}
}
""",
        encoding="utf-8",
    )
    source["writing_task"]["references_seed"] = [
        {"id": "seed-bib", "type": "bibtex", "path": bib_path.relative_to(repo_root).as_posix()}
    ]
    input_path = tmp_path / "literature_input.json"
    output_path = tmp_path / "literature_report.json"
    input_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")

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
    assert report["citation_style"] == source["citation_style"]
    assert [paper["id"] for paper in report["papers"]] == ["yao2022react"]
    assert report["research_landscape"]["clusters"] == source["landscape"]["clusters"]
    assert report["consensus"] == source["landscape"]["consensus"]
    assert report["controversies"] == source["landscape"]["controversies"]
    assert report["research_gaps"] == source["landscape"]["research_gaps"]
    assert len(report["formatted_bibliography"]["gb7714"]) == 1
    assert len(report["formatted_bibliography"]["apa"]) == 1
    assert "unmapped_papers" not in report
