from __future__ import annotations

import argparse
import json
from pathlib import Path

from cite import format_bibliography
from ingest import ingest_references
from merge import build_literature_report
from validate import ContractError, validate_report_input


def main() -> int:
    args = _parse()
    data = _load(args.input)
    try:
        validate_report_input(data)
        papers = ingest_references(data, Path(args.input).resolve().parent)
        bibliography = format_bibliography(papers)
        report = build_literature_report(data, papers, bibliography)
    except ContractError as exc:
        _write(args.output, {"artifact_type": "literature_report", "error": {"message": str(exc), "fields": exc.fields}})
        return 1

    _write(args.output, {"artifact_type": "literature_report", "literature_report": report})
    return 0


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(path: str, payload: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
