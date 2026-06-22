from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from format_refs import format_references, render_reference_lines
from normalize import normalize_draft
from validate import (
    ContractError,
    FormattingConstraints,
    compute_quality_checks,
    detect_format_issues,
    extract_draft,
    parse_formatting_constraints,
    validate_markdown_length,
)

Issue = dict[str, Any]


def main() -> int:
    args = _parse()
    data = _load(args.input)
    try:
        constraints = parse_formatting_constraints(data)
        draft = extract_draft(data)
        normalized, issues = _process_draft(draft, constraints)
        markdown = _render_markdown(normalized, constraints)
        validate_markdown_length(markdown)
    except ContractError as exc:
        _write(args.output, {"artifact_type": "formatted_draft", "error": {"message": str(exc), "fields": exc.fields}})
        return 1

    markdown_path = str(Path(args.output).with_suffix(".md"))
    Path(markdown_path).write_text(markdown, encoding="utf-8")
    formatted = {
        "normalized_draft": normalized,
        "markdown": markdown,
        "markdown_path": markdown_path,
        "issues": issues,
        "quality_checks": compute_quality_checks(issues),
    }
    _write(args.output, {"artifact_type": "formatted_draft", "formatted_draft": formatted})
    return 0


def _process_draft(draft: dict[str, Any], constraints: FormattingConstraints) -> tuple[dict[str, Any], list[Issue]]:
    normalized, norm_issues = normalize_draft(draft, constraints)
    normalized, ref_issues = format_references(normalized, constraints)
    fixed_issues = [*norm_issues, *(issue for issue in ref_issues if issue.get("severity") == "fixed")]
    warning_issues = detect_format_issues(normalized, constraints)
    return normalized, [*fixed_issues, *warning_issues]


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def _load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(path: str, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _render_markdown(draft: dict[str, Any], constraints: FormattingConstraints) -> str:
    lines: list[str] = []
    title = str(draft.get("title") or "未命名论文").strip()
    lines.extend([f"# {title}", ""])
    abstract = str(draft.get("abstract") or "").strip()
    if abstract:
        lines.extend(_abstract_block(abstract, constraints.abstract_heading))
    keywords = [str(item).strip() for item in draft.get("keywords", []) if str(item).strip()]
    if keywords:
        lines.extend(["**关键词**：" + "；".join(keywords), ""])
    for section in draft.get("sections", []):
        if not isinstance(section, dict):
            continue
        level = max(2, min(int(section.get("level") or 1) + 1, 6))
        title_text = str(section.get("title") or "").strip()
        content = str(section.get("content_markdown") or "").strip()
        if not title_text or not content:
            continue
        lines.extend([f"{'#' * level} {title_text}", "", content, ""])
    references = draft.get("references")
    if isinstance(references, list) and references:
        lines.extend(["## 参考文献", ""])
        lines.extend(render_reference_lines(references, bibliography_style=constraints.bibliography_style))
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _abstract_block(abstract: str, abstract_heading: str) -> list[str]:
    heading = abstract_heading.strip() or "## 摘要"
    match = re.match(r"^(#+)\s+(.+)$", heading)
    if match:
        return [f"{match.group(1)} {match.group(2)}", "", abstract, ""]
    return [heading, "", abstract, ""]


if __name__ == "__main__":
    raise SystemExit(main())
