from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


def _run_script(repo_root: Path, input_path: Path, output_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(repo_root / "skill_packs" / "academic-paper-writing" / "skills" / "academic-formatting" / "scripts" / "run.py"),
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


def test_happy_path_clean_draft(tmp_path):
    repo_root = Path.cwd()
    assets = repo_root / "skill_packs" / "academic-paper-writing" / "skills" / "academic-formatting" / "assets"
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "formatted_draft.json"
    # draft.sample.json omits formatting_constraints; script should apply GB/T 7714 defaults.
    input_path.write_text((assets / "draft.sample.json").read_text(encoding="utf-8"), encoding="utf-8")

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    formatted = payload["formatted_draft"]
    assert payload["artifact_type"] == "formatted_draft"
    assert formatted["quality_checks"]["headings_normalized"] is True
    assert formatted["quality_checks"]["references_formatted"] is True
    assert formatted["issues"] == []
    assert len(formatted["markdown"]) >= 3000
    markdown_path = Path(formatted["markdown_path"])
    assert markdown_path.exists()
    assert markdown_path.read_text(encoding="utf-8") == formatted["markdown"]


def test_normalizes_messy_draft(tmp_path):
    repo_root = Path.cwd()
    assets = repo_root / "skill_packs" / "academic-paper-writing" / "skills" / "academic-formatting" / "assets"
    example = json.loads((assets / "input.example.json").read_text(encoding="utf-8"))
    raw_wrapper = json.loads((assets / "draft.raw.sample.json").read_text(encoding="utf-8"))
    messy_input = {
        "draft": raw_wrapper["draft"],
        "formatting_constraints": example["formatting_constraints"],
    }
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "formatted_draft.json"
    input_path.write_text(json.dumps(messy_input, ensure_ascii=False), encoding="utf-8")

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    formatted = payload["formatted_draft"]
    issues = formatted["issues"]
    fixed_codes = {issue["code"] for issue in issues if issue["severity"] == "fixed"}
    assert issues
    assert "heading_level_jump" in fixed_codes
    assert "citation_style_inconsistent" in fixed_codes
    assert formatted["quality_checks"]["headings_normalized"] is True
    assert formatted["quality_checks"]["references_formatted"] is True

    normalized = formatted["normalized_draft"]
    levels = [section["level"] for section in normalized["sections"] if section.get("title")]
    assert levels[1] == 2  # raw sample had level 3 jump after level 1
    prev = 0
    for level in levels:
        assert level <= prev + 1
        prev = level

    for section in normalized["sections"]:
        content = section.get("content_markdown", "")
        assert "[[" not in content
        assert "[(" not in content
        assert re.search(r"(?<!\[)\(\d+\)(?!\])", content) is None

    assert "## 参考文献" in formatted["markdown"]
    assert re.search(r"^\[\d+\] ", formatted["markdown"], re.MULTILINE)


def test_missing_draft_fails(tmp_path):
    repo_root = Path.cwd()
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "formatted_draft.json"
    input_path.write_text(json.dumps({"formatting_constraints": {"citation_style": "GB/T 7714"}}, ensure_ascii=False), encoding="utf-8")

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "formatted_draft"
    assert "error" in payload


def test_empty_sections_fails(tmp_path):
    repo_root = Path.cwd()
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "formatted_draft.json"
    input_path.write_text(
        json.dumps(
            {
                "draft": {
                    "title": "测试",
                    "abstract": "摘要",
                    "keywords": ["关键词"],
                    "sections": [],
                    "references": [],
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "error" in payload
    assert "draft.sections" in payload["error"]["fields"]
