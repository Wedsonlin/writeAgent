"""State and trace JSON I/O helpers for the local ReAct graph."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


def load_state(state_path: Path) -> dict[str, Any]:
    try:
        if not state_path.exists():
            return {}
        data = json.loads(state_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def write_state(state_path: Path, state: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(state_path, state)


def write_trace(trace_path: Path, status: str, steps: list[dict[str, Any]]) -> None:
    payload = {"status": status, "steps": steps}
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(trace_path, payload)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        shutil.move(tmp, path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


__all__ = ["atomic_write_json", "load_state", "write_state", "write_trace"]
