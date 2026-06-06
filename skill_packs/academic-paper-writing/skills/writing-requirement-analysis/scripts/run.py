from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    args = _parse()
    data = _load(args.input)
    text = data.get("user_request") or data.get("request") or data.get("topic") or "?????"
    task = {
        "topic": data.get("topic") or _first_line(text),
        "paper_type": data.get("paper_type", "survey"),
        "language": data.get("language", "zh"),
        "target_journal": data.get("target_journal", {"name": "???", "level": "???", "style_profile": {"citation_style": data.get("citation_style", "GB/T 7714")}}),
        "word_limit": data.get("word_limit", {"total": 8000}),
        "core_arguments": data.get("core_arguments") or ["????????????????????"],
        "innovation_points": data.get("innovation_points") or [],
        "research_scope": data.get("research_scope", {"domain": "????", "subtopics": []}),
        "chapter_framework": data.get("chapter_framework") or [
            {"chapter_id": "1", "title": "??", "key_points": ["????", "????"], "word_budget": 1000},
            {"chapter_id": "2", "title": "????", "key_points": ["????", "????"], "word_budget": 2000},
            {"chapter_id": "3", "title": "?????", "key_points": ["????", "?????"], "word_budget": 3500},
            {"chapter_id": "4", "title": "??", "key_points": ["??", "????"], "word_budget": 1000},
        ],
        "references_seed": data.get("references_seed", []),
        "missing_info": [],
    }
    _write(args.output, {"artifact_type": "writing_task", "writing_task": task})
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


def _first_line(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip()), "?????")[:120]


if __name__ == "__main__":
    raise SystemExit(main())
