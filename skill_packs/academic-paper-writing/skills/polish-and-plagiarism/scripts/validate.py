from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

Issue = dict[str, Any]

TONE_ACADEMIC_ISSUE_CODES = frozenset(
    {
        "informal_tone",
        "citation_marker_changed",
        "bibliography_changed",
        "heading_structure_changed",
        "repetitive_phrasing",
        "workflow_process_artifact",
    }
)

_REQUIRED_POLISH_LOG_FIELDS = ("section", "change_type", "reason")
_MIN_MARKDOWN_LENGTH = 3000


@dataclass
class ContractError(Exception):
    message: str
    fields: list[str]

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class PolishConstraints:
    tone: str = "formal-zh"
    language: str = "zh"
    preserve_citations: bool = True
    preserve_headings: bool = True


def parse_polish_constraints(data: dict[str, Any]) -> PolishConstraints:
    raw = data.get("polish_constraints")
    if not isinstance(raw, dict):
        return PolishConstraints()

    tone = str(raw.get("tone") or "formal-zh")
    language = str(raw.get("language") or "zh")
    preserve_citations = raw.get("preserve_citations")
    preserve_headings = raw.get("preserve_headings")
    return PolishConstraints(
        tone=tone,
        language=language,
        preserve_citations=True if preserve_citations is None else bool(preserve_citations),
        preserve_headings=True if preserve_headings is None else bool(preserve_headings),
    )


def extract_formatted_markdown(data: dict[str, Any]) -> str | None:
    formatted = data.get("formatted_draft")
    if not isinstance(formatted, dict):
        return None
    nested = formatted.get("formatted_draft")
    if isinstance(nested, dict):
        formatted = nested
    markdown = str(formatted.get("markdown") or "").strip()
    return markdown if markdown else None


def extract_polished_markdown(data: dict[str, Any]) -> str:
    polished = str(data.get("polished_markdown") or "").strip()
    if polished:
        return polished + "\n"
    formatted_markdown = extract_formatted_markdown(data)
    if formatted_markdown and data.get("accept_formatted_without_changes") is True:
        return formatted_markdown + "\n"
    raise ContractError(
        "polish input must include LLM-polished markdown in polished_markdown",
        ["polished_markdown"],
    )


def validate_markdown_length(markdown: str, min_length: int = _MIN_MARKDOWN_LENGTH) -> None:
    if len(markdown.strip()) < min_length:
        raise ContractError("polished markdown is too short for a paper artifact", ["polished_markdown"])


def validate_polish_log(raw_log: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_log, list) or not raw_log:
        raise ContractError("polish_log must be a non-empty array of edit records", ["polish_log"])

    validated: list[dict[str, Any]] = []
    for index, entry in enumerate(raw_log):
        field_prefix = f"polish_log[{index}]"
        if not isinstance(entry, dict):
            raise ContractError("each polish_log entry must be an object", [field_prefix])
        for key in _REQUIRED_POLISH_LOG_FIELDS:
            value = entry.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ContractError(
                    f"polish_log entry is missing required field {key!r}",
                    [f"{field_prefix}.{key}"],
                )
        validated.append(entry)
    return validated


def protected_claim_issues(claims: Any, markdown: str) -> list[Issue]:
    if not isinstance(claims, list) or not claims:
        return []

    issues: list[Issue] = []
    for index, claim in enumerate(claims):
        text = str(claim or "").strip()
        if not text:
            continue
        if text not in markdown:
            issues.append(
                {
                    "code": "protected_claim_rephrased",
                    "severity": "warning",
                    "field": f"protected_claims[{index}]",
                    "message": "protected claim was not preserved verbatim; verify semantic preservation manually",
                }
            )
    return issues


def validate_blocking_contract(data: dict[str, Any], markdown: str) -> dict[str, Any]:
    validate_markdown_length(markdown)
    polish_log = validate_polish_log(data.get("polish_log"))
    return {
        "polish_log": polish_log,
        "plagiarism_optimization": _as_list(data.get("plagiarism_optimization")),
        "constraints": parse_polish_constraints(data),
        "formatted_markdown": extract_formatted_markdown(data),
        "source_formatted_path": _source_formatted_path(data),
        "protected_claim_issues": protected_claim_issues(data.get("protected_claims"), markdown),
    }


def compute_quality_checks(
    issues: list[Issue],
    polish_log: list[dict[str, Any]] | None = None,
    export_status: dict[str, Any] | None = None,
) -> dict[str, bool]:
    def has_unresolved_warning(codes: frozenset[str]) -> bool:
        return any(
            issue.get("severity") == "warning" and issue.get("code") in codes for issue in issues
        )

    polish_log_present = bool(polish_log)
    if polish_log:
        polish_log_present = all(
            isinstance(entry, dict)
            and all(str(entry.get(key) or "").strip() for key in _REQUIRED_POLISH_LOG_FIELDS)
            for entry in polish_log
        )

    checks = {
        "polish_log_present": polish_log_present,
        "tone_academic": not has_unresolved_warning(TONE_ACADEMIC_ISSUE_CODES),
        "protected_claims_preserved": not any(
            issue.get("severity") == "warning" and issue.get("code") == "protected_claim_rephrased"
            for issue in issues
        ),
    }
    if export_status is not None:
        checks["docx_exported"] = export_status.get("docx", {}).get("status") == "generated"
        checks["pdf_exported"] = export_status.get("pdf", {}).get("status") == "generated"
    return checks


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _source_formatted_path(data: dict[str, Any]) -> str | None:
    formatted = data.get("formatted_draft")
    if not isinstance(formatted, dict):
        return None
    nested = formatted.get("formatted_draft")
    if isinstance(nested, dict):
        formatted = nested
    path = formatted.get("markdown_path")
    return str(path) if isinstance(path, str) and path.strip() else None


def list_value(data: dict[str, Any], key: str) -> list[Any]:
    return _as_list(data.get(key))
