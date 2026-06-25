"""Shared Markdown-to-document export helpers for writeAgent skills."""

from __future__ import annotations

import json
import re
import subprocess
import textwrap
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


JOS_TEMPLATE_PROFILE = "journal_of_software_2025"
JOS_TEMPLATE_SOURCE = "case/references/软件学报排版样例2025年版.doc"
_CITATION_RUN_RE = re.compile(r"\[(?:\d+(?:\s*[,，\-–—−]\s*\d+)*)\]")
_REFERENCE_HEADING_RE = re.compile(r"^(?:参考文献|References)$", re.IGNORECASE)
_REFERENCE_LINE_RE = re.compile(r"^(\[\d+\]\s+)(.*)$")
_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


class DocumentExportError(RuntimeError):
    """Raised when a required export cannot be produced."""


def export_markdown_document(
    markdown: str,
    output_base: str | Path,
    *,
    title: str | None = None,
    template_profile: str | None = None,
    template_source_path: str | None = None,
) -> dict[str, Any]:
    """Export a Markdown paper to DOCX and, when possible, PDF.

    DOCX is a required artifact for Skill5/6, so DOCX failures raise
    ``DocumentExportError``. PDF export is optional: missing dependencies,
    fonts, or rendering issues are recorded as ``unavailable`` in the returned
    status instead of failing the skill contract.
    """

    profile = normalize_template_profile(template_profile, template_source_path)
    base = Path(output_base)
    base.parent.mkdir(parents=True, exist_ok=True)
    docx_path = base.with_suffix(".docx")
    pdf_path = base.with_suffix(".pdf")

    _write_docx(markdown, docx_path, title=title, template_profile=profile)
    export_status: dict[str, Any] = {
        "docx": {
            "status": "generated",
            "path": str(docx_path),
        }
    }

    exported_pdf_path = _export_pdf(markdown, docx_path, pdf_path, title=title, template_profile=profile)
    export_status["pdf"] = exported_pdf_path["status"]

    return {
        "docx_path": str(docx_path),
        "pdf_path": exported_pdf_path["path"],
        "export_status": export_status,
        "template_profile": profile,
        "template_source_path": template_source_path or (JOS_TEMPLATE_SOURCE if profile == JOS_TEMPLATE_PROFILE else None),
        "template_conformance_report": build_template_conformance_report(docx_path, profile),
    }


def normalize_template_profile(
    template_profile: str | None,
    template_source_path: str | None = None,
) -> str | None:
    profile = str(template_profile or "").strip()
    if profile:
        return profile
    source = str(template_source_path or "").strip()
    if "软件学报排版样例" in source or "journal_of_software" in source.lower():
        return JOS_TEMPLATE_PROFILE
    sample = Path(JOS_TEMPLATE_SOURCE)
    if sample.exists():
        return JOS_TEMPLATE_PROFILE
    return None


def build_template_conformance_report(docx_path: str | Path, template_profile: str | None) -> dict[str, Any]:
    profile = normalize_template_profile(template_profile)
    if profile != JOS_TEMPLATE_PROFILE:
        return {"profile": profile or "default", "checks": {}, "passed": True}

    checks = {
        "body_citations_superscript": False,
        "reference_numbers_not_superscript": False,
        "page_setup_matches_template": False,
        "heading_styles_match_template": False,
    }
    try:
        checks["body_citations_superscript"] = _body_citations_are_superscript(Path(docx_path))
        checks["reference_numbers_not_superscript"] = _reference_numbers_are_not_superscript(Path(docx_path))
        checks["page_setup_matches_template"] = _page_setup_matches_jos(Path(docx_path))
        checks["heading_styles_match_template"] = _heading_styles_match_jos(Path(docx_path))
    except Exception as exc:  # pragma: no cover - report should be best effort.
        return {
            "profile": profile,
            "checks": checks,
            "passed": False,
            "error": str(exc),
        }
    return {
        "profile": profile,
        "checks": checks,
        "passed": all(checks.values()),
    }


def _write_docx(markdown: str, path: Path, *, title: str | None, template_profile: str | None) -> None:
    try:
        from docx import Document
    except ImportError as exc:  # pragma: no cover - exercised in integration environments.
        raise DocumentExportError("python-docx is required to export DOCX") from exc

    try:
        document = Document()
        _configure_docx_styles(document, template_profile=template_profile)
        first_heading_written = False
        in_references = False
        pending: list[str] = []

        def flush_pending() -> None:
            if not pending:
                return
            paragraph_text = " ".join(line.strip() for line in pending if line.strip()).strip()
            pending.clear()
            if paragraph_text:
                _add_body_paragraph(document, paragraph_text, template_profile=template_profile)

        for raw_line in markdown.splitlines():
            line = raw_line.rstrip()
            if not line.strip():
                flush_pending()
                continue

            heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
            if heading:
                flush_pending()
                level = len(heading.group(1))
                text = _strip_inline_markdown(heading.group(2))
                in_references = bool(_REFERENCE_HEADING_RE.match(text))
                _add_heading(
                    document,
                    text or title or "",
                    level=level,
                    first_heading=level == 1 and not first_heading_written,
                    template_profile=template_profile,
                    is_references=in_references,
                )
                if level == 1 and not first_heading_written:
                    first_heading_written = True
                continue

            if in_references or _is_reference_line(line):
                flush_pending()
                _add_reference_paragraph(document, _strip_inline_markdown(line), template_profile=template_profile)
                continue

            if _is_list_line(line):
                flush_pending()
                paragraph = document.add_paragraph(style="List Bullet")
                _add_runs_with_optional_superscript(
                    paragraph,
                    _strip_inline_markdown(line.lstrip("-*0123456789. ")),
                    superscript_citations=template_profile == JOS_TEMPLATE_PROFILE,
                    template_profile=template_profile,
                )
                _format_paragraph(paragraph, first_line_indent=False, template_profile=template_profile)
                continue

            if _is_table_line(line):
                flush_pending()
                paragraph = document.add_paragraph()
                _add_runs_with_optional_superscript(
                    paragraph,
                    _strip_inline_markdown(line),
                    superscript_citations=template_profile == JOS_TEMPLATE_PROFILE,
                    template_profile=template_profile,
                )
                _format_paragraph(paragraph, first_line_indent=False, template_profile=template_profile)
                continue

            pending.append(line)

        flush_pending()
        path.parent.mkdir(parents=True, exist_ok=True)
        document.save(path)
    except DocumentExportError:
        raise
    except Exception as exc:  # pragma: no cover - depends on python-docx internals.
        raise DocumentExportError(f"failed to export DOCX: {exc}") from exc


def _configure_docx_styles(document: Any, *, template_profile: str | None) -> None:
    from docx.shared import Cm, Pt

    if template_profile == JOS_TEMPLATE_PROFILE:
        section = document.sections[0]
        section.page_width = Cm(18.4)
        section.page_height = Cm(26.0)
        section.top_margin = Cm(1.0)
        section.bottom_margin = Cm(2.2)
        section.left_margin = Cm(1.5)
        section.right_margin = Cm(1.5)
        _set_style_font(document.styles["Normal"], "Times New Roman", "SimSun", 9)
        document.styles["Normal"].paragraph_format.line_spacing = 12.0
        _set_style_font(document.styles["Title"], "Times New Roman", "SimHei", 18)
        _set_style_font(document.styles["Heading 1"], "Times New Roman", "SimHei", 10.5)
        _set_style_font(document.styles["Heading 2"], "Times New Roman", "SimHei", 9)
        _set_style_font(document.styles["Heading 3"], "Times New Roman", "SimHei", 9)
        for style_name in ("Title", "Heading 1", "Heading 2", "Heading 3"):
            document.styles[style_name].paragraph_format.line_spacing = 12.0
        return

    chinese_font = "SimSun"
    normal = document.styles["Normal"]
    normal.font.name = chinese_font
    normal.font.size = Pt(12)
    _set_east_asia_font(normal.font, chinese_font)
    normal.paragraph_format.line_spacing = 1.5

    for style_name in ("Title", "Heading 1", "Heading 2", "Heading 3", "Heading 4"):
        try:
            style = document.styles[style_name]
        except KeyError:
            continue
        style.font.name = chinese_font
        _set_east_asia_font(style.font, chinese_font)


def _set_style_font(style: Any, ascii_font: str, east_asia_font: str, size_pt: float) -> None:
    from docx.shared import Pt

    style.font.name = ascii_font
    style.font.size = Pt(size_pt)
    _set_east_asia_font(style.font, east_asia_font)


def _set_east_asia_font(font: Any, font_name: str) -> None:
    try:
        from docx.oxml.ns import qn

        font.element.rPr.rFonts.set(qn("w:eastAsia"), font_name)
    except Exception:
        return


def _add_heading(
    document: Any,
    text: str,
    *,
    level: int,
    first_heading: bool,
    template_profile: str | None,
    is_references: bool,
) -> None:
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    if template_profile == JOS_TEMPLATE_PROFILE:
        if first_heading:
            paragraph = document.add_paragraph(style="Title")
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _add_plain_run(paragraph, text, template_profile=template_profile, size_pt=18, east_asia_font="SimHei")
            return
        if is_references:
            paragraph = document.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            _format_paragraph(paragraph, first_line_indent=False, template_profile=template_profile, heading=True)
            _add_plain_run(paragraph, text, template_profile=template_profile, size_pt=9, east_asia_font="SimHei", bold=True)
            return
        mapped_level = max(1, min(level - 1, 3))
        paragraph = document.add_heading("", mapped_level)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        _add_plain_run(
            paragraph,
            text,
            template_profile=template_profile,
            size_pt=10.5 if mapped_level == 1 else 9,
            east_asia_font="SimHei",
        )
        return

    if first_heading:
        paragraph = document.add_heading(text, 0)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        document.add_heading(text, min(level, 4))


def _add_body_paragraph(document: Any, text: str, *, template_profile: str | None) -> None:
    paragraph = document.add_paragraph()
    _add_runs_with_optional_superscript(
        paragraph,
        _strip_inline_markdown(text),
        superscript_citations=template_profile == JOS_TEMPLATE_PROFILE,
        template_profile=template_profile,
    )
    _format_paragraph(paragraph, template_profile=template_profile)


def _add_reference_paragraph(document: Any, text: str, *, template_profile: str | None) -> None:
    paragraph = document.add_paragraph()
    match = _REFERENCE_LINE_RE.match(text)
    if match:
        _add_plain_run(paragraph, match.group(1), template_profile=template_profile, size_pt=7.5 if template_profile == JOS_TEMPLATE_PROFILE else None)
        _add_plain_run(paragraph, match.group(2), template_profile=template_profile, size_pt=7.5 if template_profile == JOS_TEMPLATE_PROFILE else None)
    else:
        _add_plain_run(paragraph, text, template_profile=template_profile, size_pt=7.5 if template_profile == JOS_TEMPLATE_PROFILE else None)
    _format_paragraph(
        paragraph,
        first_line_indent=False,
        hanging_reference=True,
        template_profile=template_profile,
    )


def _add_runs_with_optional_superscript(
    paragraph: Any,
    text: str,
    *,
    superscript_citations: bool,
    template_profile: str | None,
) -> None:
    position = 0
    for match in _CITATION_RUN_RE.finditer(text):
        if match.start() > position:
            _add_plain_run(paragraph, text[position : match.start()], template_profile=template_profile)
        run = _add_plain_run(paragraph, match.group(0), template_profile=template_profile)
        if superscript_citations:
            run.font.superscript = True
        position = match.end()
    if position < len(text):
        _add_plain_run(paragraph, text[position:], template_profile=template_profile)


def _add_plain_run(
    paragraph: Any,
    text: str,
    *,
    template_profile: str | None,
    size_pt: float | None = None,
    east_asia_font: str | None = None,
    bold: bool = False,
) -> Any:
    from docx.shared import Pt

    run = paragraph.add_run(text)
    if template_profile == JOS_TEMPLATE_PROFILE:
        run.font.name = "Times New Roman"
        run.font.size = Pt(size_pt or 9)
        run.font.bold = bold
        _set_east_asia_font(run.font, east_asia_font or "SimSun")
    return run


def _format_paragraph(
    paragraph: Any,
    *,
    first_line_indent: bool = True,
    hanging_reference: bool = False,
    template_profile: str | None,
    heading: bool = False,
) -> None:
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Cm, Pt

    if template_profile == JOS_TEMPLATE_PROFILE:
        paragraph.paragraph_format.line_spacing = 12.0
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT if heading else WD_ALIGN_PARAGRAPH.JUSTIFY
        if hanging_reference:
            paragraph.paragraph_format.left_indent = Pt(20.1)
            paragraph.paragraph_format.first_line_indent = Pt(-20.1)
        elif first_line_indent:
            paragraph.paragraph_format.first_line_indent = Pt(15.6)
        return

    paragraph.paragraph_format.line_spacing = 1.5
    paragraph.paragraph_format.space_after = Cm(0.08)
    if hanging_reference:
        paragraph.paragraph_format.left_indent = Cm(0.74)
        paragraph.paragraph_format.first_line_indent = Cm(-0.74)
    elif first_line_indent:
        paragraph.paragraph_format.first_line_indent = Cm(0.74)


def _export_pdf(
    markdown: str,
    docx_path: Path,
    pdf_path: Path,
    *,
    title: str | None,
    template_profile: str | None,
) -> dict[str, Any]:
    try:
        if template_profile == JOS_TEMPLATE_PROFILE:
            _write_pdf_from_docx_with_word(docx_path, pdf_path)
        else:
            _write_pdf(markdown, pdf_path, title=title)
    except Exception as first_exc:
        try:
            _write_pdf(markdown, pdf_path, title=title)
        except Exception as fallback_exc:  # PDF is explicitly best-effort.
            return {
                "status": {
                    "status": "unavailable",
                    "path": None,
                    "reason": f"{first_exc}; fallback failed: {fallback_exc}",
                },
                "path": None,
            }
    return {
        "status": {
            "status": "generated",
            "path": str(pdf_path),
        },
        "path": str(pdf_path),
    }


def _write_pdf_from_docx_with_word(docx_path: Path, pdf_path: Path) -> None:
    script = f"""
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $word.Documents.Open({json.dumps(str(docx_path.resolve()))}, $false, $true)
try {{
  $doc.SaveAs([ref]{json.dumps(str(pdf_path.resolve()))}, [ref]17)
}} finally {{
  $doc.Close($false)
  $word.Quit()
}}
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "Word COM PDF conversion failed").strip())


def _write_pdf(markdown: str, path: Path, *, title: str | None) -> None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise RuntimeError("reportlab is not installed") from exc

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    page_width, page_height = A4
    left = 54
    top = page_height - 54
    bottom = 54
    y = top
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle(title or _first_heading(markdown) or "writeAgent paper")

    def new_page() -> None:
        nonlocal y
        c.showPage()
        c.setFont("STSong-Light", 10.5)
        y = top

    c.setFont("STSong-Light", 10.5)
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            y -= 10
            if y < bottom:
                new_page()
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        font_size = 10.5
        if heading:
            line = heading.group(2)
            font_size = max(12, 18 - len(heading.group(1)))
        c.setFont("STSong-Light", font_size)
        for piece in _wrap_cjk(_strip_inline_markdown(line), max_chars=42 if font_size <= 11 else 28):
            if y < bottom:
                new_page()
                c.setFont("STSong-Light", font_size)
            c.drawString(left, y, piece)
            y -= font_size + 6
        y -= 3

    path.parent.mkdir(parents=True, exist_ok=True)
    c.save()


def _body_citations_are_superscript(docx_path: Path) -> bool:
    paragraphs = _read_docx_paragraph_runs(docx_path)
    seen = False
    in_references = False
    for runs in paragraphs:
        paragraph_text = "".join(text for text, _ in runs)
        if _REFERENCE_HEADING_RE.match(paragraph_text.strip()):
            in_references = True
            continue
        if in_references:
            continue
        for text, superscript in runs:
            if _CITATION_RUN_RE.fullmatch(text):
                seen = True
                if not superscript:
                    return False
    return seen


def _reference_numbers_are_not_superscript(docx_path: Path) -> bool:
    paragraphs = _read_docx_paragraph_runs(docx_path)
    in_references = False
    seen = False
    for runs in paragraphs:
        paragraph_text = "".join(text for text, _ in runs)
        if _REFERENCE_HEADING_RE.match(paragraph_text.strip()):
            in_references = True
            continue
        if not in_references:
            continue
        for text, superscript in runs:
            if re.match(r"^\[\d+\]", text):
                seen = True
                if superscript:
                    return False
    return seen


def _page_setup_matches_jos(docx_path: Path) -> bool:
    from docx import Document

    section = Document(str(docx_path)).sections[0]
    return (
        round(section.page_width.cm, 1) == 18.4
        and round(section.page_height.cm, 1) == 26.0
        and round(section.top_margin.cm, 1) == 1.0
        and round(section.bottom_margin.cm, 1) == 2.2
        and round(section.left_margin.cm, 1) == 1.5
        and round(section.right_margin.cm, 1) == 1.5
    )


def _heading_styles_match_jos(docx_path: Path) -> bool:
    from docx import Document

    document = Document(str(docx_path))
    return (
        document.styles["Normal"].font.size.pt == 9
        and document.styles["Heading 1"].font.size.pt == 10.5
        and document.styles["Heading 2"].font.size.pt == 9
    )


def _read_docx_paragraph_runs(docx_path: Path) -> list[list[tuple[str, bool]]]:
    with zipfile.ZipFile(docx_path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    paragraphs: list[list[tuple[str, bool]]] = []
    for paragraph in root.findall(".//w:p", _NS):
        runs: list[tuple[str, bool]] = []
        for run in paragraph.findall("w:r", _NS):
            text = "".join(node.text or "" for node in run.findall("w:t", _NS))
            if not text:
                continue
            vert = run.find("w:rPr/w:vertAlign", _NS)
            superscript = vert is not None and vert.attrib.get(f"{{{_NS['w']}}}val") == "superscript"
            runs.append((text, superscript))
        if runs:
            paragraphs.append(runs)
    return paragraphs


def _strip_inline_markdown(text: str) -> str:
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    return text.strip()


def _is_list_line(line: str) -> bool:
    return bool(re.match(r"\s*(?:[-*]\s+|\d+[.)]\s+)", line))


def _is_reference_line(line: str) -> bool:
    return bool(_REFERENCE_LINE_RE.match(line.strip()))


def _is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def _first_heading(markdown: str) -> str | None:
    for line in markdown.splitlines():
        match = re.match(r"^#\s+(.+)$", line.strip())
        if match:
            return _strip_inline_markdown(match.group(1))
    return None


def _wrap_cjk(text: str, *, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    return textwrap.wrap(text, width=max_chars, replace_whitespace=False, drop_whitespace=False) or [text]
