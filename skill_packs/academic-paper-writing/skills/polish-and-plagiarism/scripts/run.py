from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from diff_check import detect_polish_issues
from validate import (
    ContractError,
    compute_quality_checks,
    extract_polished_markdown,
    validate_blocking_contract,
)

Issue = dict[str, Any]


def main() -> int:
    args = _parse()
    data = _load(args.input)
    try:
        markdown = extract_polished_markdown(data)
        context = validate_blocking_contract(data, markdown)
        issues = detect_polish_issues(
            context["formatted_markdown"],
            markdown,
            context["constraints"],
        )
    except ContractError as exc:
        _write(args.output, {"artifact_type": "polished_draft", "error": {"message": str(exc), "fields": exc.fields}})
        return 1

    markdown_path = str(Path(args.output).with_suffix(".md"))
    Path(markdown_path).write_text(markdown, encoding="utf-8")
    polish_log = context["polish_log"]
    polished = {
        "markdown": markdown,
        "markdown_path": markdown_path,
        "polish_log": polish_log,
        "plagiarism_optimization": context["plagiarism_optimization"],
        "issues": issues,
        "quality_checks": compute_quality_checks(issues, polish_log),
        "source_formatted_path": context["source_formatted_path"],
    }
    _write(args.output, {"artifact_type": "polished_draft", "polished_draft": polished})
    return 0


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


if __name__ == "__main__":
    raise SystemExit(main())
