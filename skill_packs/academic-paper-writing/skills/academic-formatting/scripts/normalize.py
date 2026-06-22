from __future__ import annotations

import copy
import re
from typing import Any

from validate import FormattingConstraints, Issue

_CITATION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\[\[\s*(\d+)\s*\]\]"), r"[\1]"),
    (re.compile(r"\[\(\s*(\d+)\s*\)\]"), r"[\1]"),
    (re.compile(r"\[\s+(\d+)\s+\]"), r"[\1]"),
    (re.compile(r"(?<!\[)\((\d+)\)(?!\])"), r"[\1]"),
]


def normalize_draft(draft: dict[str, Any], constraints: FormattingConstraints) -> tuple[dict[str, Any], list[Issue]]:
    normalized = copy.deepcopy(draft)
    issues: list[Issue] = []
    issues.extend(_normalize_headings(normalized, constraints))
    issues.extend(_normalize_section_citations(normalized))
    return normalized, issues


def normalize_headings(draft: dict[str, Any], constraints: FormattingConstraints) -> list[Issue]:
    working = copy.deepcopy(draft)
    return _normalize_headings(working, constraints)


def normalize_citations(draft: dict[str, Any]) -> list[Issue]:
    working = copy.deepcopy(draft)
    return _normalize_section_citations(working)


def _normalize_headings(draft: dict[str, Any], constraints: FormattingConstraints) -> list[Issue]:
    issues: list[Issue] = []
    prev_level = 0

    for index, section in enumerate(draft.get("sections", [])):
        if not isinstance(section, dict):
            continue
        field = f"draft.sections[{index}].level"
        title = str(section.get("title") or "").strip()
        content = str(section.get("content_markdown") or "").strip()
        if not title or not content:
            continue

        level = _coerce_level(section.get("level"), default=1)
        new_level = level
        message: str | None = None

        if prev_level == 0 and level != 1:
            new_level = 1
            message = f"remapped first section level from {level} to 1"
        elif prev_level > 0 and level > prev_level + 1:
            new_level = prev_level + 1
            message = f"remapped heading level from {level} to {new_level} to remove jump after level {prev_level}"
        if new_level > constraints.max_level:
            if new_level != constraints.max_level:
                message = (
                    message or f"remapped heading level from {level} to {constraints.max_level}"
                )
            new_level = constraints.max_level

        if new_level != level:
            section["level"] = new_level
            issues.append(
                {
                    "code": "heading_level_jump",
                    "severity": "fixed",
                    "field": field,
                    "message": message or f"remapped heading level from {level} to {new_level}",
                }
            )

        prev_level = new_level

    return issues


def _normalize_section_citations(draft: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    for index, section in enumerate(draft.get("sections", [])):
        if not isinstance(section, dict):
            continue
        content = str(section.get("content_markdown") or "")
        if not content:
            continue
        normalized_content, changed = _normalize_citation_markers(content)
        if changed:
            section["content_markdown"] = normalized_content
            issues.append(
                {
                    "code": "citation_style_inconsistent",
                    "severity": "fixed",
                    "field": f"draft.sections[{index}].content_markdown",
                    "message": "normalized in-text citation markers to [n] form",
                }
            )
    return issues


def _normalize_citation_markers(content: str) -> tuple[str, bool]:
    updated = content
    changed = False
    for pattern, replacement in _CITATION_PATTERNS:
        new_content, count = pattern.subn(replacement, updated)
        if count:
            changed = True
            updated = new_content
    return updated, changed


def _coerce_level(value: Any, default: int = 1) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default
