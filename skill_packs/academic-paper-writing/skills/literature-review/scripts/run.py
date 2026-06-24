from __future__ import annotations

import argparse
import json
from pathlib import Path

from cite import format_bibliography
from ingest import ingest_references
from merge import build_literature_report
from render import render_literature_report_markdown
from validate import ContractError, validate_report_input


def main() -> int:
    args = _parse()
    data = _load(args.input)
    _hydrate_task_book_markdown(data, Path(args.input).resolve().parent)
    try:
        validate_report_input(data)
        papers = ingest_references(data, Path(args.input).resolve().parent)
        bibliography = format_bibliography(papers)
        report = build_literature_report(data, papers, bibliography)
        markdown = render_literature_report_markdown(report)
    except ContractError as exc:
        _write(args.output, {"artifact_type": "literature_report", "error": {"message": str(exc), "fields": exc.fields}})
        return 1

    markdown_path = str(Path(args.output).with_suffix(".md"))
    Path(markdown_path).write_text(markdown, encoding="utf-8")
    _write(
        args.output,
        {
            "artifact_type": "literature_report",
            "literature_report": report,
            "literature_report_markdown": markdown,
            "literature_report_markdown_path": markdown_path,
        },
    )
    return 0


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hydrate_task_book_markdown(data: dict, input_dir: Path) -> None:
    if data.get("task_book_markdown") or not data.get("task_book_markdown_path"):
        return
    raw = str(data.get("task_book_markdown_path") or "")
    candidate = Path(raw)
    candidates = [candidate] if candidate.is_absolute() else [Path.cwd() / candidate, input_dir / candidate]
    for path in candidates:
        if path.exists():
            data["task_book_markdown"] = path.read_text(encoding="utf-8")
            return


def _write(path: str, payload: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
