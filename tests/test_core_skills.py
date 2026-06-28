from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


SKILLS = Path("skill_packs") / "academic-paper-writing" / "skills"


def test_core_stage_scripts_emit_formal_artifacts(tmp_path):
    repo = Path.cwd()

    stage1 = _run_skill(
        repo,
        "writing-requirement-analysis",
        SKILLS / "writing-requirement-analysis" / "assets" / "input.example.json",
        tmp_path / "artifacts" / "01-论文写作任务书.json",
    )
    assert stage1["artifact_type"] == "writing_task"
    assert Path(stage1["task_book_markdown_path"]).name == "01-论文写作任务书.md"

    literature_input = tmp_path / "tmp" / "stage2-input.json"
    literature_input.parent.mkdir(parents=True, exist_ok=True)
    literature_input.write_text(json.dumps(_literature_input(repo, tmp_path), ensure_ascii=False), encoding="utf-8")
    stage2 = _run_skill(
        repo,
        "literature-review",
        literature_input,
        tmp_path / "artifacts" / "02-文献处理报告.json",
    )
    assert stage2["artifact_type"] == "literature_report"
    assert Path(stage2["literature_report_markdown_path"]).name == "02-文献处理报告.md"
    assert stage2["literature_report"]["papers"]

    outline_input = tmp_path / "tmp" / "stage3-input.json"
    outline_input.parent.mkdir(parents=True, exist_ok=True)
    outline_input.write_text(json.dumps(_outline_input(), ensure_ascii=False), encoding="utf-8")
    stage3 = _run_skill(repo, "paper-outline", outline_input, tmp_path / "artifacts" / "03-论文详细大纲.json")
    assert stage3["artifact_type"] == "outline"
    assert Path(stage3["outline_markdown_path"]).name == "03-论文详细大纲.md"
    assert stage3["outline"]["sections"]

    content_input = tmp_path / "tmp" / "stage4-input.json"
    content_input.write_text(json.dumps(_content_input(), ensure_ascii=False), encoding="utf-8")
    stage4 = _run_skill(repo, "paper-content-generation", content_input, tmp_path / "artifacts" / "04-分章节初稿.json")
    assert stage4["artifact_type"] == "draft"
    assert Path(stage4["draft"]["draft_markdown_path"]).name == "04-分章节初稿.md"
    assert stage4["draft"]["quality_checks"]["citations_valid"] is True

    stage5 = _run_skill(
        repo,
        "academic-formatting",
        SKILLS / "academic-formatting" / "assets" / "draft.sample.json",
        tmp_path / "artifacts" / "05-格式规范的论文终稿.json",
    )
    formatted = stage5["formatted_draft"]
    assert stage5["artifact_type"] == "formatted_draft"
    assert Path(formatted["markdown_path"]).name == "05-格式规范的论文终稿.md"
    assert Path(formatted["docx_path"]).name == "05-格式规范的论文终稿.docx"
    assert zipfile.is_zipfile(formatted["docx_path"])

    stage6 = _run_skill(
        repo,
        "polish-and-plagiarism",
        SKILLS / "polish-and-plagiarism" / "assets" / "polished.sample.json",
        tmp_path / "artifacts" / "06-润色论文终稿.json",
    )
    polished = stage6["polished_draft"]
    assert stage6["artifact_type"] == "polished_draft"
    assert polished["quality_checks"]["tone_academic"] is True
    assert polished["quality_checks"]["docx_exported"] is True
    assert Path(polished["markdown_path"]).name == "06-润色论文终稿.md"
    assert Path(polished["docx_path"]).name == "06-润色论文终稿.docx"


def test_content_generation_keeps_validator_boundary_and_citation_diagnostics(tmp_path):
    repo = Path.cwd()
    payload = _content_input()
    content_input = tmp_path / "input.json"
    output_path = tmp_path / "draft.json"

    missing_draft = dict(payload)
    missing_draft.pop("draft")
    content_input.write_text(json.dumps(missing_draft, ensure_ascii=False), encoding="utf-8")
    error_payload = _run_skill(repo, "paper-content-generation", content_input, output_path, expect_success=False)
    assert error_payload["error"]["fields"] == ["draft"]

    bad_citation = _content_input()
    bad_citation["draft"]["sections"][0]["citations_used"] = ["vllm2023"]
    bad_citation["draft"]["sections"][0]["evidence_used"] = [{"paper_id": "vllm2023", "summary": "vLLM evidence"}]
    content_input.write_text(json.dumps(bad_citation, ensure_ascii=False), encoding="utf-8")
    error_payload = _run_skill(repo, "paper-content-generation", content_input, output_path, expect_success=False)
    assert "draft.sections[0].content_markdown.citation_marker" in error_payload["error"]["fields"]
    assert error_payload["error"]["details"]["citation_mismatches"][0]["expected_marker"] == 2


def test_polish_script_requires_agent_polished_markdown(tmp_path):
    repo = Path.cwd()
    example = json.loads((repo / SKILLS / "polish-and-plagiarism" / "assets" / "polished.sample.json").read_text(encoding="utf-8"))
    example.pop("polished_markdown")
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(example, ensure_ascii=False), encoding="utf-8")

    payload = _run_skill(repo, "polish-and-plagiarism", input_path, tmp_path / "06-润色论文终稿.json", expect_success=False)

    assert payload["artifact_type"] == "polished_draft"
    assert "polished_markdown" in payload["error"]["fields"]


def test_journal_template_docx_uses_fixed_pt_line_spacing(tmp_path, monkeypatch):
    from tools import document_export

    def skip_pdf(*args, **kwargs):
        return {
            "status": {"status": "unavailable", "path": None, "reason": "skipped in unit test"},
            "path": None,
        }

    monkeypatch.setattr(document_export, "_export_pdf", skip_pdf)
    markdown = (
        "# 测试论文标题\n\n"
        "## 摘要\n\n"
        "这是一段用于验证软件学报模板导出的正文，包含中文、AI Infrastructure 和引用标记[1]。\n\n"
        "## 参考文献\n\n"
        "[1] 作者. 测试文献[J]. 软件学报, 2025.\n"
    )

    exported = document_export.export_markdown_document(
        markdown,
        tmp_path / "paper",
        template_profile=document_export.JOS_TEMPLATE_PROFILE,
    )

    spacings = _docx_paragraph_spacings(Path(exported["docx_path"]))
    assert spacings
    assert all(spacing.get(f"{{{_WORD_NS['w']}}}line") != "2880" for spacing in spacings)
    assert any(spacing.get(f"{{{_WORD_NS['w']}}}line") == "240" for spacing in spacings)
    title_spacing = _docx_style_spacing(Path(exported["docx_path"]), "Title")
    assert title_spacing
    assert title_spacing.get(f"{{{_WORD_NS['w']}}}line") == "480"
    assert exported["template_conformance_report"]["checks"].get("body_line_spacing_matches_template") is True


def test_journal_template_docx_adds_jos_front_matter(tmp_path, monkeypatch):
    from tools import document_export

    def skip_pdf(*args, **kwargs):
        return {
            "status": {"status": "unavailable", "path": None, "reason": "skipped in unit test"},
            "path": None,
        }

    monkeypatch.setattr(document_export, "_export_pdf", skip_pdf)
    exported = document_export.export_markdown_document(
        "# 测试论文标题\n\n## 摘要\n\n摘要正文。\n\n**关键词**：AI；系统\n\n## 1 引言\n\n正文内容[1]。\n\n## 参考文献\n\n1. 作者. 题名[J]. 2025.\n",
        tmp_path / "paper",
        template_profile=document_export.JOS_TEMPLATE_PROFILE,
    )

    texts = _docx_paragraph_texts(Path(exported["docx_path"]))
    assert any("软件学报 ISSN 1000-9825" in text for text in texts)
    assert any("E-mail: jos@iscas.ac.cn" in text for text in texts)
    assert any("作者信息待补充" in text for text in texts)
    assert any(text.startswith("摘  要:") for text in texts)
    assert any(text.startswith("中图法分类号:") for text in texts)
    assert any(text.startswith("中文引用格式:") for text in texts)
    assert any(text.startswith("英文引用格式:") for text in texts)
    assert any(text.startswith("Abstract:") for text in texts)
    assert _docx_paragraph_has_shading(Path(exported["docx_path"]), "中文引用格式:")
    assert any(text.startswith("[1] 作者.") for text in texts)
    assert exported["template_conformance_report"]["checks"].get("reference_numbers_not_superscript") is True
    assert not any(text == "摘要" for text in texts)
    title_colors = _docx_paragraph_run_colors(Path(exported["docx_path"]), "测试论文标题")
    assert title_colors
    assert set(title_colors) <= {"000000", None}
    assert not _docx_style_has_paragraph_border(Path(exported["docx_path"]), "Title")


def test_journal_template_docx_matches_requested_front_matter_typography(tmp_path, monkeypatch):
    from tools import document_export

    def skip_pdf(*args, **kwargs):
        return {
            "status": {"status": "unavailable", "path": None, "reason": "skipped in unit test"},
            "path": None,
        }

    monkeypatch.setattr(document_export, "_export_pdf", skip_pdf)
    exported = document_export.export_markdown_document(
        "# 测试论文标题：中文（示例）\n\n"
        "## 摘要\n\n"
        "摘要正文，包含中文标点；以及“引号”和（括号）。\n\n"
        "**关键词**：AI；系统\n\n"
        "## 1 引言\n\n"
        "正文内容，继续测试中文标点。\n\n"
        "## 参考文献\n\n"
        "1. 作者. 题名[J]. 2025.\n",
        tmp_path / "paper",
        template_profile=document_export.JOS_TEMPLATE_PROFILE,
    )
    docx_path = Path(exported["docx_path"])

    assert _docx_paragraph_alignment(docx_path, "测试论文标题:中文(示例)") == "left"
    assert _docx_paragraph_run_sizes(docx_path, "测试论文标题:中文(示例)") == ["28"]
    assert set(_docx_paragraph_east_asia_fonts(docx_path, "摘  要:")) <= {"KaiTi"}
    assert set(_docx_paragraph_east_asia_fonts(docx_path, "作者信息待补充")) <= {"FangSong"}
    assert set(_docx_paragraph_east_asia_fonts(docx_path, "(单位信息待补充)")) <= {"SimSun"}
    assert _docx_paragraph_run_sizes(docx_path, "(单位信息待补充)") == ["16"]
    assert all(size == "15" for size in _docx_runs_with_text_sizes(docx_path, "软件学报 ISSN 1000-9825"))
    assert not _docx_has_header_text(docx_path)

    combined_text = "\n".join(_docx_paragraph_texts(docx_path))
    assert not any(mark in combined_text for mark in "，。；：（）“”")
    assert "摘要正文,包含中文标点;以及\"引号\"和(括号)." in combined_text


_WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def _docx_paragraph_texts(docx_path: Path) -> list[str]:
    with zipfile.ZipFile(docx_path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    return ["".join(node.text or "" for node in paragraph.findall(".//w:t", _WORD_NS)) for paragraph in root.findall(".//w:p", _WORD_NS)]


def _docx_paragraph_run_colors(docx_path: Path, paragraph_text: str) -> list[str | None]:
    with zipfile.ZipFile(docx_path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    for paragraph in root.findall(".//w:p", _WORD_NS):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", _WORD_NS))
        if text != paragraph_text:
            continue
        colors = []
        for run in paragraph.findall("w:r", _WORD_NS):
            color = run.find("w:rPr/w:color", _WORD_NS)
            colors.append(color.attrib.get(f"{{{_WORD_NS['w']}}}val") if color is not None else None)
        return colors
    return []


def _docx_paragraph_alignment(docx_path: Path, paragraph_text: str) -> str | None:
    paragraph = _find_docx_paragraph(docx_path, paragraph_text)
    if paragraph is None:
        return None
    alignment = paragraph.find("w:pPr/w:jc", _WORD_NS)
    return alignment.attrib.get(f"{{{_WORD_NS['w']}}}val") if alignment is not None else None


def _docx_paragraph_run_sizes(docx_path: Path, paragraph_text: str) -> list[str | None]:
    paragraph = _find_docx_paragraph(docx_path, paragraph_text)
    if paragraph is None:
        return []
    sizes = []
    for run in paragraph.findall("w:r", _WORD_NS):
        if not "".join(node.text or "" for node in run.findall("w:t", _WORD_NS)):
            continue
        size = run.find("w:rPr/w:sz", _WORD_NS)
        sizes.append(size.attrib.get(f"{{{_WORD_NS['w']}}}val") if size is not None else None)
    return sizes


def _docx_paragraph_east_asia_fonts(docx_path: Path, text_prefix: str) -> list[str | None]:
    paragraph = _find_docx_paragraph(docx_path, text_prefix, startswith=True)
    if paragraph is None:
        return []
    fonts = []
    for run in paragraph.findall("w:r", _WORD_NS):
        if not "".join(node.text or "" for node in run.findall("w:t", _WORD_NS)):
            continue
        r_fonts = run.find("w:rPr/w:rFonts", _WORD_NS)
        fonts.append(r_fonts.attrib.get(f"{{{_WORD_NS['w']}}}eastAsia") if r_fonts is not None else None)
    return fonts


def _docx_runs_with_text_sizes(docx_path: Path, text_prefix: str) -> list[str | None]:
    paragraph = _find_docx_paragraph(docx_path, text_prefix, startswith=True)
    if paragraph is None:
        return []
    sizes = []
    for run in paragraph.findall("w:r", _WORD_NS):
        if not "".join(node.text or "" for node in run.findall("w:t", _WORD_NS)):
            continue
        size = run.find("w:rPr/w:sz", _WORD_NS)
        sizes.append(size.attrib.get(f"{{{_WORD_NS['w']}}}val") if size is not None else None)
    return sizes


def _docx_has_header_text(docx_path: Path) -> bool:
    with zipfile.ZipFile(docx_path) as archive:
        header_names = [name for name in archive.namelist() if name.startswith("word/header") and name.endswith(".xml")]
        for name in header_names:
            root = ET.fromstring(archive.read(name))
            if "".join(node.text or "" for node in root.findall(".//w:t", _WORD_NS)).strip():
                return True
    return False


def _find_docx_paragraph(docx_path: Path, text: str, *, startswith: bool = False) -> ET.Element | None:
    with zipfile.ZipFile(docx_path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    for paragraph in root.findall(".//w:p", _WORD_NS):
        paragraph_text = "".join(node.text or "" for node in paragraph.findall(".//w:t", _WORD_NS))
        if paragraph_text == text or (startswith and paragraph_text.startswith(text)):
            return paragraph
    return None


def _docx_paragraph_spacings(docx_path: Path, *, style_id: str | None = None) -> list[dict[str, str]]:
    with zipfile.ZipFile(docx_path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    spacings = []
    for paragraph in root.findall(".//w:p", _WORD_NS):
        paragraph_style = paragraph.find("w:pPr/w:pStyle", _WORD_NS)
        if style_id is not None and (
            paragraph_style is None or paragraph_style.attrib.get(f"{{{_WORD_NS['w']}}}val") != style_id
        ):
            continue
        spacing = paragraph.find("w:pPr/w:spacing", _WORD_NS)
        if spacing is not None:
            spacings.append(dict(spacing.attrib))
    return spacings


def _docx_style_spacing(docx_path: Path, style_id: str) -> dict[str, str] | None:
    with zipfile.ZipFile(docx_path) as archive:
        root = ET.fromstring(archive.read("word/styles.xml"))
    style = root.find(f".//w:style[@w:styleId='{style_id}']", _WORD_NS)
    if style is None:
        return None
    spacing = style.find("w:pPr/w:spacing", _WORD_NS)
    return dict(spacing.attrib) if spacing is not None else None


def _docx_style_has_paragraph_border(docx_path: Path, style_id: str) -> bool:
    with zipfile.ZipFile(docx_path) as archive:
        root = ET.fromstring(archive.read("word/styles.xml"))
    style = root.find(f".//w:style[@w:styleId='{style_id}']", _WORD_NS)
    return style is not None and style.find("w:pPr/w:pBdr", _WORD_NS) is not None


def _docx_paragraph_has_shading(docx_path: Path, text_prefix: str) -> bool:
    with zipfile.ZipFile(docx_path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    for paragraph in root.findall(".//w:p", _WORD_NS):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", _WORD_NS))
        if not text.startswith(text_prefix):
            continue
        return paragraph.find("w:pPr/w:shd", _WORD_NS) is not None
    return False


def _run_skill(
    repo: Path,
    skill: str,
    input_path: Path,
    output_path: Path,
    *,
    expect_success: bool = True,
) -> dict:
    script = repo / SKILLS / skill / "scripts" / "run.py"
    result = subprocess.run(
        [sys.executable, str(script), "--input", str(input_path), "--output", str(output_path)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_success:
        assert result.returncode == 0, result.stderr or output_path.read_text(encoding="utf-8")
    else:
        assert result.returncode == 1
    return json.loads(output_path.read_text(encoding="utf-8"))


def _outline_input() -> dict:
    argument = "AI Infra has evolved from isolated compute supply to cross-layer system engineering."
    innovation = "Build a layered taxonomy for large-model AI infrastructure."
    return {
        "writing_task": {
            "topic": "Large-model AI infrastructure",
            "paper_type": "survey",
            "word_limit": {"total": 3200},
            "core_arguments": [argument],
            "innovation_points": [innovation],
            "chapter_framework": [
                {"chapter_id": "1", "title": "Introduction", "key_points": ["background", "problem"]},
                {"chapter_id": "2", "title": "Training and inference infrastructure", "key_points": ["training", "serving"]},
                {"chapter_id": "3", "title": "Future challenges", "key_points": ["cost", "energy"]},
            ],
        },
        "literature_report": {
            "papers": [
                {"id": "zero2020", "title": "ZeRO", "evidence_strength": "moderate"},
                {"id": "vllm2023", "title": "vLLM", "evidence_strength": "moderate"},
            ],
            "argument_support_matrix": [
                {
                    "argument": argument,
                    "supporting_papers": ["zero2020", "vllm2023"],
                    "support_strength": "moderate",
                    "evidence_summaries": ["ZeRO and vLLM show cross-layer system optimization."],
                    "gap": "",
                }
            ],
            "innovation_support_matrix": [
                {
                    "innovation": innovation,
                    "supporting_papers": ["zero2020", "vllm2023"],
                    "support_strength": "moderate",
                    "evidence_summaries": ["The papers support a taxonomy spanning training and inference."],
                    "gap": "",
                }
            ],
        },
    }


def _literature_input(repo: Path, tmp_path: Path) -> dict:
    payload = json.loads((repo / SKILLS / "literature-review" / "assets" / "input.example.json").read_text(encoding="utf-8"))
    bib_path = tmp_path / "tmp" / "seed.bib"
    bib_path.parent.mkdir(parents=True, exist_ok=True)
    bib_path.write_text(
        """@misc{yao2022react,
  author = {Yao, Shunyu and Zhao, Jeffrey and Yu, Dian},
  title = {ReAct: Synergizing Reasoning and Acting in Language Models},
  year = {2022},
  eprint = {2210.03629},
  archivePrefix = {arXiv}
}
""",
        encoding="utf-8",
    )
    payload["writing_task"]["references_seed"] = [
        {
            "id": "seed-bib",
            "type": "bibtex",
            "path": str(bib_path),
        }
    ]
    return payload


def _content_input() -> dict:
    argument = "AI Infra has evolved from isolated compute supply to cross-layer system engineering."
    innovation = "Build a layered taxonomy for large-model AI infrastructure."
    sections = [
        _section("1", "Introduction", argument, innovation, "zero2020"),
        _section("2", "Training infrastructure", argument, innovation, "zero2020"),
        _section("3", "Inference infrastructure", argument, innovation, "vllm2023"),
        _section("4", "Operations and governance", argument, innovation, "vllm2023", support_status="weak"),
        _section("5", "Conclusion", argument, innovation, "zero2020"),
    ]
    return {
        "outline_markdown": "# Outline\n",
        "literature_report_markdown": "# Literature\n",
        "writing_task": {
            "topic": "Large-model AI infrastructure",
            "paper_type": "survey",
            "core_arguments": [argument],
            "innovation_points": [innovation],
        },
        "outline": {
            "sections": [{"section_id": str(i), "title": s["title"], "level": 1, "word_budget": 420} for i, s in enumerate(sections, 1)],
            "argument_coverage": [{"argument": argument, "section_ids": ["1", "2", "3", "4", "5"]}],
            "innovation_coverage": [{"innovation": innovation, "section_ids": ["1", "2", "3", "4", "5"]}],
        },
        "literature_report": {
            "paper_reading_cards": [
                {"paper_id": "zero2020", "reading_status": "read", "source_urls": ["https://example.com/zero"]},
                {"paper_id": "vllm2023", "reading_status": "read", "source_urls": ["https://example.com/vllm"]},
            ],
            "argument_support_matrix": [
                {"argument": argument, "supporting_papers": ["zero2020", "vllm2023"], "support_strength": "moderate"}
            ],
            "innovation_support_matrix": [
                {"innovation": innovation, "supporting_papers": ["zero2020", "vllm2023"], "support_strength": "moderate"}
            ],
            "references": [
                {"id": "zero2020", "title": "ZeRO", "gb7714": "Rajbhandari S, et al. ZeRO[C]. 2020."},
                {"id": "vllm2023", "title": "vLLM", "gb7714": "Kwon W, et al. vLLM[C]. 2023."},
            ],
        },
        "draft": {
            "title": "Large-model AI infrastructure",
            "abstract": _section_text("This survey frames large-model AI infrastructure as a cross-layer system problem.", "[1]"),
            "keywords": ["AI Infra", "large models", "distributed training", "inference serving"],
            "sections": sections,
            "references": [
                {"id": "zero2020", "title": "ZeRO", "gb7714": "Rajbhandari S, et al. ZeRO[C]. 2020."},
                {"id": "vllm2023", "title": "vLLM", "gb7714": "Kwon W, et al. vLLM[C]. 2023."},
            ],
            "argument_trace": [{"argument": argument, "section_ids": ["1", "2", "3", "4", "5"], "support_status": "moderate"}],
            "innovation_trace": [{"innovation": innovation, "section_ids": ["1", "2", "3", "4", "5"], "support_status": "moderate"}],
            "unsupported_claims": ["Comparable energy and cost metrics still require more cross-platform data."],
            "open_questions": ["How can heterogeneous accelerators be evaluated under a unified cost model?"],
        },
    }


def _section(section_id: str, title: str, argument: str, innovation: str, paper_id: str, *, support_status: str = "moderate") -> dict:
    marker = "[1]" if paper_id == "zero2020" else "[2]"
    return {
        "id": section_id,
        "source_outline_section_id": section_id,
        "title": title,
        "level": 1,
        "target_word_count": 420,
        "content_markdown": _section_text(f"{title} analyzes the architecture and scheduling mechanism of AI infrastructure.", marker),
        "citations_used": [paper_id],
        "linked_core_arguments": [argument],
        "linked_innovation_points": [innovation],
        "evidence_used": [{"paper_id": paper_id, "summary": "The cited paper provides system evidence."}],
        "data_used": [],
        "transition_in": "This section continues the previous system framing.",
        "transition_out": "The next section compares another layer of the infrastructure stack.",
        "support_status": support_status,
        "section_depth_checks": {
            "problem_framed": True,
            "mechanism_explained": True,
            "evidence_interpreted": True,
            "comparison_or_tradeoff": True,
            "limitation_or_boundary": True,
            "argument_return": True,
        },
    }


def _section_text(seed: str, marker: str) -> str:
    sentences = [
        f"{seed} The problem is not only raw compute supply but also the coordination of memory, communication, runtime scheduling, and service isolation {marker}. ",
        "The mechanism works through layered resource control, cache management, parallel execution, and feedback from observable system metrics. ",
        "Prior evidence and paper results show that memory partitioning, request batching, and compiler optimization can shift the bottleneck across layers. ",
        "Compared with a single accelerator benchmark, this tradeoff view explains why throughput, latency, cost, and reliability must be analyzed together. ",
        "The limitation is that cost and energy data are often platform-specific, so the boundary of the claim should remain explicit. ",
        "Therefore, the section returns to the main argument: AI Infra should be evaluated as a cross-layer system rather than a single component. ",
        "This also supports the innovation because a layered taxonomy gives each representative system a clear position in the survey. ",
        "Future work still needs unified measurement for heterogeneous clusters and multi-tenant inference workloads. ",
    ]
    return "".join(sentences * 4)
