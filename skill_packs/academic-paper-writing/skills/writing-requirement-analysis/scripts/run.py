from __future__ import annotations

import argparse
import json
from pathlib import Path

from contract_builder import ContractError, build_writing_task_payload


def main() -> int:
    args = _parse()
    try:
        payload = build_writing_task_payload(_load(args.input), output_path=args.output)
    except ContractError as exc:
        _write_error(args.output, exc)
        return 1

    _write(args.output, payload)
    _write_task_book(payload)
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


def _write_task_book(payload: dict) -> None:
    markdown_path = payload.get("task_book_markdown_path")
    markdown = payload.get("task_book_markdown")
    if not markdown_path or not isinstance(markdown, str):
        return
    path = Path(str(markdown_path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")


def _write_error(path: str, exc: ContractError) -> None:
    payload = {
        "artifact_type": "writing_task",
        "error": {"message": str(exc), "missing_fields": exc.missing_fields},
    }
    _write(path, payload)


if __name__ == "__main__":
    raise SystemExit(main())
