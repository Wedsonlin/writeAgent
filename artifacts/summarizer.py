"""Small deterministic artifact summarizer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def summarize_artifact(path: str | Path, *, max_chars: int = 500) -> str:
    p = Path(path)
    if not p.exists():
        return "missing artifact file"
    text = p.read_text(encoding="utf-8", errors="replace")
    try:
        payload: Any = json.loads(text)
        if isinstance(payload, dict):
            keys = ", ".join(sorted(payload.keys())[:12])
            return f"JSON object with keys: {keys}"
    except json.JSONDecodeError:
        pass
    compact = " ".join(text.split())
    return compact[:max_chars]
