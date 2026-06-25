from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


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
    assert polished["export_status"]["docx"]["status"] == "generated"
    assert polished["export_status"]["pdf"]["status"] in {"generated", "unavailable"}
    assert polished["polish_report"]["total_polish_changes"] >= 1
    markdown_path = Path(polished["markdown_path"])
    assert markdown_path.exists()
    assert markdown_path.read_text(encoding="utf-8") == polished["markdown"]
    docx_path = Path(polished["docx_path"])
    assert docx_path.exists()
    assert docx_path.stat().st_size > 0
    assert zipfile.is_zipfile(docx_path)
    if polished.get("pdf_path"):
        pdf_path = Path(polished["pdf_path"])
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0


def test_polished_draft_inherits_journal_template_profile(tmp_path):
    repo_root = Path.cwd()
    assets = _skill_assets(repo_root)
    example = json.loads((assets / "polished.sample.json").read_text(encoding="utf-8"))
    example["formatted_draft"]["template_profile"] = "journal_of_software_2025"
    example["formatted_draft"]["template_source_path"] = "case/references/软件学报排版样例2025年版.doc"
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "polished_draft.json"
    input_path.write_text(json.dumps(example, ensure_ascii=False), encoding="utf-8")

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    polished = payload["polished_draft"]
    assert polished["template_profile"] == "journal_of_software_2025"
    assert polished["template_source_path"].endswith("软件学报排版样例2025年版.doc")
    assert polished["template_conformance_report"]["checks"]["body_citations_superscript"] is True

    document_xml = _docx_xml(Path(polished["docx_path"]))
    assert _has_superscript_text(document_xml, "[1]")


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


def test_detects_workflow_process_artifacts_without_banning_natural_stage_word(tmp_path):
    repo_root = Path.cwd()
    assets = _skill_assets(repo_root)
    example = json.loads((assets / "polished.sample.json").read_text(encoding="utf-8"))
    marker = "\n## 参考文献"
    leak = "\n\n自然语言处理的发展阶段体现了模型能力演进的学术脉络。本阶段生成的 Skill5 产物已经写入 scripts/run.py。\n"
    example["polished_markdown"] = example["polished_markdown"].replace(marker, leak + marker)
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "polished_draft.json"
    input_path.write_text(json.dumps(example, ensure_ascii=False), encoding="utf-8")

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    polished = payload["polished_draft"]
    issue_codes = {issue["code"] for issue in polished["issues"]}
    assert "workflow_process_artifact" in issue_codes
    assert polished["quality_checks"]["tone_academic"] is False


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


def test_formatted_draft_path_fallback_exports_final_artifact(tmp_path):
    repo_root = Path.cwd()
    assets = _skill_assets(repo_root)
    example = json.loads((assets / "input.example.json").read_text(encoding="utf-8"))
    formatted_path = tmp_path / "formatted_draft.json"
    formatted_path.write_text(
        json.dumps({"artifact_type": "formatted_draft", "formatted_draft": example["formatted_draft"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "polished_draft.json"
    input_path.write_text(
        json.dumps(
            {
                "formatted_draft_path": str(formatted_path),
                "polish_constraints": example["polish_constraints"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    polished = payload["polished_draft"]
    issue_codes = {issue["code"] for issue in polished["issues"]}
    assert "formatted_markdown_fallback" in issue_codes
    assert polished["quality_checks"]["polish_log_present"] is True
    assert Path(polished["docx_path"]).exists()


def test_formatted_draft_path_with_polished_markdown_auto_logs(tmp_path):
    repo_root = Path.cwd()
    assets = _skill_assets(repo_root)
    example = json.loads((assets / "input.example.json").read_text(encoding="utf-8"))
    formatted_path = tmp_path / "formatted_draft.json"
    formatted_path.write_text(
        json.dumps({"artifact_type": "formatted_draft", "formatted_draft": example["formatted_draft"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "polished_draft.json"
    input_path.write_text(
        json.dumps(
            {
                "formatted_draft_path": str(formatted_path),
                "polished_markdown": example["formatted_draft"]["markdown"].replace("本文", "本文主要", 1),
                "polish_constraints": example["polish_constraints"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 0, result.stderr
    polished = json.loads(output_path.read_text(encoding="utf-8"))["polished_draft"]
    issue_codes = {issue["code"] for issue in polished["issues"]}
    assert "auto_polish_log" in issue_codes
    assert polished["quality_checks"]["polish_log_present"] is True


def test_rephrased_protected_claim_warns_without_blocking(tmp_path):
    repo_root = Path.cwd()
    assets = _skill_assets(repo_root)
    example = json.loads((assets / "polished.sample.json").read_text(encoding="utf-8"))
    example["protected_claims"] = ["this exact protected claim is intentionally absent"]
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "polished_draft.json"
    input_path.write_text(json.dumps(example, ensure_ascii=False), encoding="utf-8")

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    polished = payload["polished_draft"]
    issue_codes = {issue["code"] for issue in polished["issues"]}
    assert "protected_claim_rephrased" in issue_codes
    assert polished["quality_checks"]["protected_claims_preserved"] is False
    assert polished["quality_checks"]["docx_exported"] is True


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


def _docx_xml(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read("word/document.xml"))


def _has_superscript_text(root: ET.Element, text: str) -> bool:
    for run in root.findall(".//w:r", NS):
        value = "".join(node.text or "" for node in run.findall("w:t", NS))
        if value != text:
            continue
        vert = run.find("w:rPr/w:vertAlign", NS)
        if vert is not None and vert.attrib.get(f"{{{NS['w']}}}val") == "superscript":
            return True
    return False
