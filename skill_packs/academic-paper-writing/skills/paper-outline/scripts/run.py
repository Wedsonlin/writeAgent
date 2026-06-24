from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    args = _parse()
    data = _load(args.input)
    task = data.get("writing_task", {})
    framework = task.get("chapter_framework") or []
    allocated_budgets = _chapter_budgets(task, len([item for item in framework if isinstance(item, dict)]))
    sections = [
        {
            "id": str(item.get("chapter_id", idx + 1)),
            "title": item.get("title", f"Section {idx + 1}"),
            "level": 1,
            "parent_id": None,
            "key_points": item.get("key_points", []),
            "transition_note": "",
            "word_budget": item.get("word_budget") if item.get("word_budget") is not None else allocated_budgets[idx],
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


def _chapter_budgets(task: dict, count: int) -> list[int]:
    if count <= 0:
        return []
    word_limit = task.get("word_limit") if isinstance(task.get("word_limit"), dict) else {}
    by_chapter = word_limit.get("by_chapter")
    if isinstance(by_chapter, list) and len(by_chapter) >= count:
        return [int(value) for value in by_chapter[:count]]
    total = int(word_limit.get("total") or 8000)
    base = total // count
    budgets = [base for _ in range(count)]
    budgets[-1] += total - sum(budgets)
    return budgets


if __name__ == "__main__":
    raise SystemExit(main())
