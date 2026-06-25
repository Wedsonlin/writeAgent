from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any

Issue = dict[str, Any]

HEADING_ISSUE_CODES = frozenset({"heading_level_jump", "missing_section_title"})
REFERENCE_ISSUE_CODES = frozenset(
    {
        "citation_style_inconsistent",
        "missing_gb7714",
        "citation_id_unmapped",
        "citation_index_out_of_range",
    }
)
CAPTION_ISSUE_CODES = frozenset({"figure_caption_missing", "table_caption_missing"})

_CITATION_INDEX_RE = re.compile(r"\[(\d+)\]")
_NON_CANONICAL_CITATION_RE = re.compile(
    r"\[\[\s*(\d+)\s*\]\]"
    r"|\[\(\s*(\d+)\s*\)\]"
    r"|\[\s+(\d+)\s+\]"
    r"|(?<!\[)\((\d+)\)(?!\])"
)


@dataclass
class ContractError(Exception):
    message: str
    fields: list[str]

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class FormattingConstraints:
    citation_style: str = "GB/T 7714"
    max_level: int = 3
    abstract_heading: str = "## 摘要"
    in_text_style: str = "numeric-bracket"
    bibliography_style: str = "gb7714"
    export_format: str = "markdown"
    template_profile: str | None = None
    template_source_path: str | None = None


def extract_draft(data: dict[str, Any]) -> dict[str, Any]:
    draft = data.get("draft")
    if isinstance(draft, dict) and isinstance(draft.get("draft"), dict):
        draft = draft["draft"]
    if not isinstance(draft, dict):
        raise ContractError("formatting input must include the full draft object", ["draft"])
    sections = draft.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ContractError("draft.sections is required", ["draft.sections"])
    references = draft.get("references")
    if _sections_have_citations(sections) and (not isinstance(references, list) or not references):
        raise ContractError(
            "draft.references is required when draft sections contain [n] citations",
            ["draft.references"],
        )
    return draft


def parse_formatting_constraints(data: dict[str, Any]) -> FormattingConstraints:
    raw = data.get("formatting_constraints")
    if not isinstance(raw, dict):
        return FormattingConstraints(
            template_profile=_default_template_profile(),
            template_source_path=_default_template_source_path(),
        )

    heading_rules = raw.get("heading_rules")
    reference_rules = raw.get("reference_rules")
    max_level = 3
    abstract_heading = "## 摘要"
    if isinstance(heading_rules, dict):
        if isinstance(heading_rules.get("max_level"), int):
            max_level = max(1, min(int(heading_rules["max_level"]), 6))
        if isinstance(heading_rules.get("abstract_heading"), str) and heading_rules["abstract_heading"].strip():
            abstract_heading = heading_rules["abstract_heading"].strip()

    in_text_style = "numeric-bracket"
    bibliography_style = "gb7714"
    if isinstance(reference_rules, dict):
        if isinstance(reference_rules.get("in_text_style"), str):
            in_text_style = reference_rules["in_text_style"]
        if isinstance(reference_rules.get("bibliography_style"), str):
            bibliography_style = reference_rules["bibliography_style"]

    citation_style = str(raw.get("citation_style") or "GB/T 7714")
    export_format = str(raw.get("export_format") or "markdown")
    template_profile = _coerce_optional_string(raw.get("template_profile")) or _profile_from_template_source(raw.get("template_source_path"))
    template_source_path = _coerce_optional_string(raw.get("template_source_path")) or _default_template_source_path()
    if template_profile is None:
        template_profile = _default_template_profile()
    return FormattingConstraints(
        citation_style=citation_style,
        max_level=max_level,
        abstract_heading=abstract_heading,
        in_text_style=in_text_style,
        bibliography_style=bibliography_style,
        export_format=export_format,
        template_profile=template_profile,
        template_source_path=template_source_path,
    )


def _coerce_optional_string(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _profile_from_template_source(value: Any) -> str | None:
    source = _coerce_optional_string(value)
    if source and ("软件学报排版样例" in source or "journal_of_software" in source.lower()):
        return "journal_of_software_2025"
    return None


def _default_template_source_path() -> str | None:
    return "case/references/软件学报排版样例2025年版.doc"


def _default_template_profile() -> str | None:
    from pathlib import Path

    return "journal_of_software_2025" if Path(_default_template_source_path() or "").exists() else None


def detect_format_issues(draft: dict[str, Any], constraints: FormattingConstraints) -> list[Issue]:
    issues: list[Issue] = []
    issues.extend(_detect_heading_issues(draft, constraints))
    issues.extend(_detect_reference_issues(draft))
    issues.extend(_detect_caption_issues(draft))
    return issues


def compute_quality_checks(issues: list[Issue], export_status: dict[str, Any] | None = None) -> dict[str, bool]:
    def has_unresolved_warning(codes: frozenset[str]) -> bool:
        return any(
            issue.get("severity") == "warning" and issue.get("code") in codes for issue in issues
        )

    checks = {
        "headings_normalized": not has_unresolved_warning(HEADING_ISSUE_CODES),
        "references_formatted": not has_unresolved_warning(REFERENCE_ISSUE_CODES),
        "figures_tables_labeled": not has_unresolved_warning(CAPTION_ISSUE_CODES),
    }
    if export_status is not None:
        checks["docx_exported"] = export_status.get("docx", {}).get("status") == "generated"
        checks["pdf_exported"] = export_status.get("pdf", {}).get("status") == "generated"
    return checks


def validate_markdown_length(markdown: str, min_length: int = 3000) -> None:
    if len(markdown) < min_length:
        raise ContractError("formatted markdown is too short for a paper artifact", ["formatted_draft.markdown"])


def _detect_heading_issues(draft: dict[str, Any], constraints: FormattingConstraints) -> list[Issue]:
    issues: list[Issue] = []
    prev_level = 0
    for index, section in enumerate(draft.get("sections", [])):
        if not isinstance(section, dict):
            continue
        field = f"draft.sections[{index}]"
        title = str(section.get("title") or "").strip()
        content = str(section.get("content_markdown") or "").strip()
        if not title:
            issues.append(
                {
                    "code": "missing_section_title",
                    "severity": "warning",
                    "field": f"{field}.title",
                    "message": "section title is empty and will be skipped during rendering",
                }
            )
            continue
        if not content:
            continue

        level = _coerce_level(section.get("level"), default=1)
        if prev_level == 0 and level != 1:
            issues.append(
                {
                    "code": "heading_level_jump",
                    "severity": "warning",
                    "field": f"{field}.level",
                    "message": f"first section level {level} should start at 1",
                }
            )
        elif prev_level > 0 and level > prev_level + 1:
            issues.append(
                {
                    "code": "heading_level_jump",
                    "severity": "warning",
                    "field": f"{field}.level",
                    "message": f"heading level jumps from {prev_level} to {level}",
                }
            )
        elif level > constraints.max_level:
            issues.append(
                {
                    "code": "heading_level_jump",
                    "severity": "warning",
                    "field": f"{field}.level",
                    "message": f"heading level {level} exceeds max_level {constraints.max_level}",
                }
            )

        if prev_level == 0:
            prev_level = 1 if level != 1 else level
        else:
            prev_level = min(level, prev_level + 1) if level > prev_level + 1 else level
        prev_level = min(prev_level, constraints.max_level)

    return issues


def _detect_reference_issues(draft: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    references = [ref for ref in draft.get("references", []) if isinstance(ref, (dict, str))]
    ref_ids = {
        str(ref.get("id"))
        for ref in references
        if isinstance(ref, dict) and ref.get("id") is not None
    }
    ref_count = len(references)

    for index, ref in enumerate(references):
        if not isinstance(ref, dict):
            continue
        if not str(ref.get("gb7714") or "").strip() and not has_renderable_reference_text(ref) and not has_structured_reference_fields(ref):
            issues.append(
                {
                    "code": "missing_gb7714",
                    "severity": "warning",
                    "field": f"draft.references[{index}].gb7714",
                    "message": "reference lacks gb7714 and structured fields to generate one",
                }
            )
        elif not str(ref.get("gb7714") or "").strip() and not has_renderable_reference_text(ref):
            issues.append(
                {
                    "code": "missing_gb7714",
                    "severity": "warning",
                    "field": f"draft.references[{index}].gb7714",
                    "message": "reference is missing gb7714 bibliography text",
                }
            )

    for section_index, section in enumerate(draft.get("sections", [])):
        if not isinstance(section, dict):
            continue
        field_prefix = f"draft.sections[{section_index}]"
        content = str(section.get("content_markdown") or "")
        if _NON_CANONICAL_CITATION_RE.search(content):
            issues.append(
                {
                    "code": "citation_style_inconsistent",
                    "severity": "warning",
                    "field": f"{field_prefix}.content_markdown",
                    "message": "in-text citations use non-canonical markers such as (n) or [[n]]",
                }
            )

        for marker in _CITATION_INDEX_RE.finditer(content):
            citation_index = int(marker.group(1))
            if citation_index < 1 or citation_index > ref_count:
                issues.append(
                    {
                        "code": "citation_index_out_of_range",
                        "severity": "warning",
                        "field": f"{field_prefix}.content_markdown",
                        "message": f"citation marker [{citation_index}] is outside references list bounds",
                    }
                )

        citations_used = section.get("citations_used")
        if not isinstance(citations_used, list):
            continue
        for citation_id in citations_used:
            citation_key = str(citation_id)
            if citation_key not in ref_ids:
                issues.append(
                    {
                        "code": "citation_id_unmapped",
                        "severity": "warning",
                        "field": f"{field_prefix}.citations_used",
                        "message": f"citations_used id {citation_key!r} is not present in draft.references",
                    }
                )

    return issues


def _detect_caption_issues(draft: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    for section_index, section in enumerate(draft.get("sections", [])):
        if not isinstance(section, dict):
            continue
        content = str(section.get("content_markdown") or "")
        field = f"draft.sections[{section_index}].content_markdown"
        if "![" in content and not re.search(r"图\s*\d+|Figure\s+\d+", content, re.IGNORECASE):
            issues.append(
                {
                    "code": "figure_caption_missing",
                    "severity": "warning",
                    "field": field,
                    "message": "figure markup is present but no numbered figure caption was found",
                }
            )
        if _contains_markdown_table(content) and not re.search(r"表\s*\d+|Table\s+\d+", content, re.IGNORECASE):
            issues.append(
                {
                    "code": "table_caption_missing",
                    "severity": "warning",
                    "field": field,
                    "message": "markdown table is present but no numbered table caption was found",
                }
            )
    return issues


def _contains_markdown_table(content: str) -> bool:
    lines = [line.strip() for line in content.splitlines()]
    for index, line in enumerate(lines[:-1]):
        if "|" not in line:
            continue
        next_line = lines[index + 1]
        if re.fullmatch(r"\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?", next_line):
            return True
    return False


def _sections_have_citations(sections: list[Any]) -> bool:
    for section in sections:
        if not isinstance(section, dict):
            continue
        if _CITATION_INDEX_RE.search(str(section.get("content_markdown") or "")):
            return True
        citations_used = section.get("citations_used")
        if isinstance(citations_used, list) and citations_used:
            return True
    return False


def _coerce_level(value: Any, default: int = 1) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def has_structured_reference_fields(ref: dict[str, Any]) -> bool:
    return bool(ref.get("authors")) and bool(ref.get("title")) and ref.get("year") is not None and bool(ref.get("type"))


def has_renderable_reference_text(ref: dict[str, Any]) -> bool:
    for key in ("gb7714", "text", "citation", "apa", "reference", "title"):
        value = ref.get(key)
        if isinstance(value, str) and value.strip():
            return True
    return False


def snapshot_draft(draft: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(draft)
