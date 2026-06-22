from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

from validate import FormattingConstraints, Issue, has_structured_reference_fields

_CITE_IMPORTED = False


def format_references(draft: dict[str, Any], constraints: FormattingConstraints) -> tuple[dict[str, Any], list[Issue]]:
    normalized = copy.deepcopy(draft)
    issues: list[Issue] = []
    references = normalized.get("references")
    if not isinstance(references, list) or not references:
        return normalized, issues

    structured_refs = [ref for ref in references if isinstance(ref, dict)]
    if constraints.bibliography_style != "gb7714" or not structured_refs:
        return normalized, issues

    format_bibliography = _load_format_bibliography()
    bibliography = format_bibliography(structured_refs)
    gb_entries = bibliography.get("gb7714", [])

    structured_index = 0
    for ref_index, ref in enumerate(references):
        if not isinstance(ref, dict):
            continue
        field = f"draft.references[{ref_index}].gb7714"
        existing = str(ref.get("gb7714") or "").strip()
        if existing:
            structured_index += 1
            continue

        if not has_structured_reference_fields(ref):
            issues.append(
                {
                    "code": "missing_gb7714",
                    "severity": "warning",
                    "field": field,
                    "message": "reference lacks gb7714 and structured fields to generate one",
                }
            )
            structured_index += 1
            continue

        if structured_index >= len(gb_entries):
            issues.append(
                {
                    "code": "missing_gb7714",
                    "severity": "warning",
                    "field": field,
                    "message": "failed to generate gb7714 bibliography entry",
                }
            )
        else:
            ref["gb7714"] = gb_entries[structured_index]
            issues.append(
                {
                    "code": "missing_gb7714",
                    "severity": "fixed",
                    "field": field,
                    "message": "generated gb7714 bibliography entry from structured reference fields",
                }
            )
        structured_index += 1

    return normalized, issues


def reference_display_text(ref: Any, *, bibliography_style: str = "gb7714") -> str:
    if isinstance(ref, str):
        return ref.strip()
    if not isinstance(ref, dict):
        return ""
    if bibliography_style == "gb7714" and ref.get("gb7714"):
        return str(ref["gb7714"]).strip()
    for key in ("gb7714", "text", "citation", "title"):
        value = ref.get(key)
        if value:
            return str(value).strip()
    return ""


def render_reference_lines(references: list[Any], *, bibliography_style: str = "gb7714") -> list[str]:
    lines: list[str] = []
    for index, ref in enumerate(references, 1):
        text = reference_display_text(ref, bibliography_style=bibliography_style)
        if text:
            lines.append(f"[{index}] {text}")
    return lines


def _load_format_bibliography():
    global _CITE_IMPORTED
    if not _CITE_IMPORTED:
        cite_scripts = Path(__file__).resolve().parents[2] / "literature-review" / "scripts"
        cite_path = str(cite_scripts)
        if cite_path not in sys.path:
            sys.path.insert(0, cite_path)
        _CITE_IMPORTED = True
    from cite import format_bibliography

    return format_bibliography
