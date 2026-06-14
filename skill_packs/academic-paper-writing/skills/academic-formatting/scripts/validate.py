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


def extract_draft(data: dict[str, Any]) -> dict[str, Any]:
    draft = data.get("draft")
    if isinstance(draft, dict) and isinstance(draft.get("draft"), dict):
        draft = draft["draft"]
    if not isinstance(draft, dict):
        raise ContractError("formatting input must include the full draft object", ["draft"])
    sections = draft.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ContractError("draft.sections is required", ["draft.sections"])
    return draft


def parse_formatting_constraints(data: dict[str, Any]) -> FormattingConstraints:
    raw = data.get("formatting_constraints")
    if not isinstance(raw, dict):
        return FormattingConstraints()

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
    return FormattingConstraints(
        citation_style=citation_style,
        max_level=max_level,
        abstract_heading=abstract_heading,
        in_text_style=in_text_style,
        bibliography_style=bibliography_style,
        export_format=export_format,
    )


def detect_format_issues(draft: dict[str, Any], constraints: FormattingConstraints) -> list[Issue]:
    issues: list[Issue] = []
    issues.extend(_detect_heading_issues(draft, constraints))
    issues.extend(_detect_reference_issues(draft))
    return issues


def compute_quality_checks(issues: list[Issue]) -> dict[str, bool]:
    def has_unresolved_warning(codes: frozenset[str]) -> bool:
        return any(
            issue.get("severity") == "warning" and issue.get("code") in codes for issue in issues
        )

    return {
        "headings_normalized": not has_unresolved_warning(HEADING_ISSUE_CODES),
        "references_formatted": not has_unresolved_warning(REFERENCE_ISSUE_CODES),
    }


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
        if not str(ref.get("gb7714") or "").strip() and not has_structured_reference_fields(ref):
            issues.append(
                {
                    "code": "missing_gb7714",
                    "severity": "warning",
                    "field": f"draft.references[{index}].gb7714",
                    "message": "reference lacks gb7714 and structured fields to generate one",
                }
            )
        elif not str(ref.get("gb7714") or "").strip():
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


def _coerce_level(value: Any, default: int = 1) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def has_structured_reference_fields(ref: dict[str, Any]) -> bool:
    return bool(ref.get("authors")) and bool(ref.get("title")) and ref.get("year") is not None and bool(ref.get("type"))


def snapshot_draft(draft: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(draft)
