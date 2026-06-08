from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ContractError(Exception):
    message: str
    fields: list[str]

    def __str__(self) -> str:
        return self.message


def main() -> int:
    args = _parse()
    data = _load(args.input)
    try:
        markdown = _extract_markdown(data)
        if len(markdown) < 3000:
            raise ContractError("polished markdown is too short for a paper artifact", ["polished_markdown"])
    except ContractError as exc:
        _write(args.output, {"artifact_type": "polished_draft", "error": {"message": str(exc), "fields": exc.fields}})
        return 1

    markdown_path = str(Path(args.output).with_suffix(".md"))
    Path(markdown_path).write_text(markdown, encoding="utf-8")
    polished = {
        "markdown": markdown,
        "markdown_path": markdown_path,
        "polish_log": _list(data.get("polish_log")),
        "plagiarism_optimization": _list(data.get("plagiarism_optimization")),
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


def _extract_markdown(data: dict[str, Any]) -> str:
    polished = str(data.get("polished_markdown") or "").strip()
    if polished:
        return polished + "\n"
    formatted = data.get("formatted_draft")
    if isinstance(formatted, dict):
        nested = formatted.get("formatted_draft")
        if isinstance(nested, dict):
            formatted = nested
        markdown = str(formatted.get("markdown") or "").strip()
        if markdown and data.get("accept_formatted_without_changes") is True:
            return markdown + "\n"
    raise ContractError(
        "polish input must include LLM-polished markdown in polished_markdown",
        ["polished_markdown"],
    )


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


if __name__ == "__main__":
    raise SystemExit(main())
