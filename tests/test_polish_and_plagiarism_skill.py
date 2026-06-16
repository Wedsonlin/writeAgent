from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _skill_assets(repo_root: Path) -> Path:
    return (
        repo_root
        / "skill_packs"
        / "academic-paper-writing"
        / "skills"
        / "polish-and-plagiarism"
        / "assets"
    )


def _run_script(repo_root: Path, input_path: Path, output_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(
                repo_root
                / "skill_packs"
                / "academic-paper-writing"
                / "skills"
                / "polish-and-plagiarism"
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


def test_happy_path_polished_sample(tmp_path):
    repo_root = Path.cwd()
    assets = _skill_assets(repo_root)
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "polished_draft.json"
    input_path.write_text((assets / "polished.sample.json").read_text(encoding="utf-8"), encoding="utf-8")

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    polished = payload["polished_draft"]
    assert payload["artifact_type"] == "polished_draft"
    assert polished["quality_checks"]["tone_academic"] is True
    assert polished["quality_checks"]["polish_log_present"] is True
    assert polished["issues"] == []
    assert len(polished["markdown"]) >= 3000
    assert polished["polish_log"]
    markdown_path = Path(polished["markdown_path"])
    assert markdown_path.exists()
    assert markdown_path.read_text(encoding="utf-8") == polished["markdown"]


def test_detects_citation_and_tone_issues(tmp_path):
    repo_root = Path.cwd()
    assets = _skill_assets(repo_root)
    raw_input = json.loads((assets / "polished.raw.sample.json").read_text(encoding="utf-8"))
    # Empty polish_log is a blocking error; inject a minimal valid log to exercise diff/tone checks.
    raw_input["polish_log"] = [
        {
            "section": "摘要",
            "change_type": "wording",
            "before": "placeholder",
            "after": "placeholder",
            "reason": "fixture for issue-detection test",
        }
    ]
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "polished_draft.json"
    input_path.write_text(json.dumps(raw_input, ensure_ascii=False), encoding="utf-8")

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    polished = payload["polished_draft"]
    issue_codes = {issue["code"] for issue in polished["issues"]}
    assert "informal_tone" in issue_codes
    assert "citation_marker_changed" in issue_codes
    assert "heading_structure_changed" in issue_codes
    assert "bibliography_changed" in issue_codes
    assert polished["quality_checks"]["tone_academic"] is False
    assert polished["quality_checks"]["polish_log_present"] is True


def test_missing_polished_markdown_fails(tmp_path):
    repo_root = Path.cwd()
    assets = _skill_assets(repo_root)
    example = json.loads((assets / "input.example.json").read_text(encoding="utf-8"))
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "polished_draft.json"
    input_path.write_text(
        json.dumps(
            {
                "formatted_draft": example["formatted_draft"],
                "polish_constraints": example["polish_constraints"],
                "polish_log": example["polish_log"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "polished_draft"
    assert "error" in payload
    assert "polished_markdown" in payload["error"]["fields"]


def test_empty_polish_log_fails(tmp_path):
    repo_root = Path.cwd()
    assets = _skill_assets(repo_root)
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "polished_draft.json"
    input_path.write_text((assets / "polished.raw.sample.json").read_text(encoding="utf-8"), encoding="utf-8")

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "error" in payload
    assert "polish_log" in payload["error"]["fields"]


def test_too_short_markdown_fails(tmp_path):
    repo_root = Path.cwd()
    assets = _skill_assets(repo_root)
    example = json.loads((assets / "input.example.json").read_text(encoding="utf-8"))
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "polished_draft.json"
    input_path.write_text(
        json.dumps(
            {
                "formatted_draft": example["formatted_draft"],
                "polished_markdown": "# 标题\n\n过短的润色稿。",
                "polish_log": example["polish_log"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "error" in payload
    assert "polished_markdown" in payload["error"]["fields"]
