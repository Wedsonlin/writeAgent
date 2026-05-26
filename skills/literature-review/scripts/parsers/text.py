"""Free-text notes → RawPaper list.

Convention: each paragraph (separated by a blank line) is one paper. Inside a
paragraph the first line is treated as the title, subsequent lines as a free
form description. This is intentionally loose so users can paste any reading
notes without forcing them into a strict schema.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def parse_text_file(path: str | Path) -> list[dict[str, Any]]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return parse_text(text)


def parse_text(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    paragraphs = re.split(r"\n\s*\n", text.strip())
    for i, para in enumerate(paragraphs):
        para = para.strip()
        if not para:
            continue
        lines = [ln.strip() for ln in para.splitlines() if ln.strip()]
        title = lines[0]
        abstract = " ".join(lines[1:]) if len(lines) > 1 else None
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", para)
        out.append(
            {
                "id": f"text-{i + 1:02d}-{re.sub(r'[^a-zA-Z0-9]+', '-', title.lower())[:30]}",
                "type": "misc",
                "title": title[:200],
                "authors": [],
                "year": int(year_match.group(0)) if year_match else 0,
                "venue": None,
                "doi": None,
                "url": None,
                "abstract": abstract,
                "source_kind": "text",
            }
        )
    return out
