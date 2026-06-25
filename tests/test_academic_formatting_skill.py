from __future__ import annotations

import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


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
    assert formatted["export_status"]["docx"]["status"] == "generated"
    assert formatted["export_status"]["pdf"]["status"] in {"generated", "unavailable"}
    assert formatted["format_check_report"]["total_issues"] == 0
    markdown_path = Path(formatted["markdown_path"])
    assert markdown_path.exists()
    assert markdown_path.read_text(encoding="utf-8") == formatted["markdown"]
    docx_path = Path(formatted["docx_path"])
    assert docx_path.exists()
    assert docx_path.stat().st_size > 0
    assert zipfile.is_zipfile(docx_path)
    if formatted.get("pdf_path"):
        pdf_path = Path(formatted["pdf_path"])
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0


def test_journal_of_software_template_profile_exports_conformant_docx(tmp_path):
    repo_root = Path.cwd()
    assets = repo_root / "skill_packs" / "academic-paper-writing" / "skills" / "academic-formatting" / "assets"
    example = json.loads((assets / "input.example.json").read_text(encoding="utf-8"))
    example.setdefault("formatting_constraints", {})["template_profile"] = "journal_of_software_2025"
    example["formatting_constraints"]["template_source_path"] = "case/references/软件学报排版样例2025年版.doc"
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "formatted_draft.json"
    input_path.write_text(json.dumps(example, ensure_ascii=False), encoding="utf-8")

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    formatted = payload["formatted_draft"]
    assert formatted["template_profile"] == "journal_of_software_2025"
    assert formatted["template_source_path"].endswith("软件学报排版样例2025年版.doc")
    report = formatted["template_conformance_report"]
    assert report["profile"] == "journal_of_software_2025"
    assert report["checks"]["body_citations_superscript"] is True
    assert report["checks"]["page_setup_matches_template"] is True
    assert report["checks"]["reference_numbers_not_superscript"] is True

    document_xml = _docx_xml(Path(formatted["docx_path"]))
    assert _has_superscript_text(document_xml, "[1]")
    assert not _reference_number_is_superscript(document_xml, "[1]")


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
    assert formatted["quality_checks"]["docx_exported"] is True
    assert formatted["export_status"]["docx"]["status"] == "generated"
    assert Path(formatted["docx_path"]).exists()
    assert formatted["format_check_report"]["fixed_issues"] >= 1

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


def test_loads_draft_from_path_input(tmp_path):
    repo_root = Path.cwd()
    assets = repo_root / "skill_packs" / "academic-paper-writing" / "skills" / "academic-formatting" / "assets"
    draft_path = tmp_path / "draft.json"
    draft_path.write_text((assets / "draft.sample.json").read_text(encoding="utf-8"), encoding="utf-8")
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "formatted_draft.json"
    input_path.write_text(
        json.dumps(
            {
                "draft_path": str(draft_path),
                "formatting_constraints": {"citation_style": "GB/T 7714"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    formatted = payload["formatted_draft"]
    assert formatted["quality_checks"]["docx_exported"] is True
    assert Path(formatted["docx_path"]).exists()


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


def test_cited_draft_without_references_fails(tmp_path):
    repo_root = Path.cwd()
    assets = repo_root / "skill_packs" / "academic-paper-writing" / "skills" / "academic-formatting" / "assets"
    sample = json.loads((assets / "draft.sample.json").read_text(encoding="utf-8"))
    draft = sample["draft"]
    draft["references"] = []
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "formatted_draft.json"
    input_path.write_text(json.dumps({"draft": draft}, ensure_ascii=False), encoding="utf-8")

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 1
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "error" in payload
    assert "draft.references" in payload["error"]["fields"]


def test_text_only_references_count_as_renderable(tmp_path):
    repo_root = Path.cwd()
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "formatted_draft.json"
    long_content = "这是一个带有可渲染文本参考文献的段落[1]。" * 120
    input_path.write_text(
        json.dumps(
            {
                "draft": {
                    "title": "测试论文",
                    "abstract": "摘要内容" * 80,
                    "keywords": ["测试"],
                    "sections": [
                        {
                            "title": "引言",
                            "level": 1,
                            "content_markdown": long_content,
                            "citations_used": ["1"],
                        }
                    ],
                    "references": [
                        {
                            "id": "1",
                            "text": "作者. 题名[J]. 期刊, 2024.",
                        }
                    ],
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = _run_script(repo_root, input_path, output_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    formatted = payload["formatted_draft"]
    assert formatted["quality_checks"]["references_formatted"] is True
    assert all(issue["code"] != "missing_gb7714" for issue in formatted["issues"])
    assert "[1] 作者. 题名[J]. 期刊, 2024." in formatted["markdown"]


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


def _reference_number_is_superscript(root: ET.Element, text: str) -> bool:
    for paragraph in root.findall(".//w:p", NS):
        paragraph_text = "".join(node.text or "" for node in paragraph.findall(".//w:t", NS))
        if "Yao S" not in paragraph_text and "ReAct" not in paragraph_text:
            continue
        for run in paragraph.findall("w:r", NS):
            value = "".join(node.text or "" for node in run.findall("w:t", NS))
            if not value.startswith(text):
                continue
            vert = run.find("w:rPr/w:vertAlign", NS)
            return vert is not None and vert.attrib.get(f"{{{NS['w']}}}val") == "superscript"
    raise AssertionError("reference paragraph not found")
