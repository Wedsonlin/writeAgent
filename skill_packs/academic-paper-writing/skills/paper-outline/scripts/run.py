from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    args = _parse()
    data = _load(args.input)
    task = data.get("writing_task", {})
    framework = task.get("chapter_framework") or []
    sections = [
        {
            "id": str(item.get("chapter_id", idx + 1)),
            "title": item.get("title", f"Section {idx + 1}"),
            "level": 1,
            "parent_id": None,
            "key_points": item.get("key_points", []),
            "transition_note": "",
            "word_budget": item.get("word_budget", 1000),
            "supporting_papers": [],
        }
        for idx, item in enumerate(framework)
        if isinstance(item, dict)
    ]
    outline = {"total_word_budget": sum(s["word_budget"] for s in sections) or 8000, "sections": sections}
    _write(args.output, {"artifact_type": "outline", "outline": outline})
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
