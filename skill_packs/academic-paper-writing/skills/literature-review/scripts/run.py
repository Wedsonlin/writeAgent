from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    args = _parse()
    data = _load(args.input)
    task = data.get("writing_task", data)
    seeds = task.get("references_seed", []) if isinstance(task, dict) else []
    papers = [
        {
            "id": item.get("id", f"seed-{idx+1}"),
            "type": item.get("type", "misc"),
            "title": item.get("raw") or item.get("path") or f"Reference {idx+1}",
            "authors": item.get("authors", []),
            "year": item.get("year"),
            "venue": item.get("venue", ""),
            "key_claims": item.get("key_claims", []),
            "evidence_strength": item.get("evidence_strength", "weak"),
            "alignment_to_core": [],
            "source_kind": item.get("type", "seed"),
        }
        for idx, item in enumerate(seeds)
        if isinstance(item, dict)
    ]
    report = {
        "keywords": [task.get("topic", "academic writing")] if isinstance(task, dict) else ["academic writing"],
        "papers": papers,
        "research_landscape": {"clusters": [], "timeline_summary": "?????????"},
        "consensus": [],
        "controversies": [],
        "research_gaps": [],
        "citation_style": data.get("citation_style") or "GB/T 7714",
        "formatted_bibliography": {"gb7714": [], "apa": []},
    }
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
