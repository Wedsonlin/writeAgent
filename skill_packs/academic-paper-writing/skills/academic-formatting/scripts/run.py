from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    args = _parse()
    data = _load(args.input)
    draft = data.get("draft", data)
    formatted = {"normalized_draft": draft, "export_paths": {"markdown": args.output}, "issues": []}
    _write(args.output, {"artifact_type": "formatted_draft", "formatted_draft": formatted})
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
