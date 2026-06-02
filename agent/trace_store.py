"""Trace writers for ReAct, Sub-agent, and LLM execution."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TraceStore:
    """Write observable execution traces under one workspace root."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.react_trace_path = self.workspace_root / "react_trace.json"
        self.subagent_trace_path = self.workspace_root / "subagent_trace.jsonl"
        self.llm_trace_path = self.workspace_root / "llm_trace.jsonl"

    def record_react_trace(self, status: str, steps: list[dict[str, Any]]) -> None:
        atomic_write_json(self.react_trace_path, {"status": status, "steps": steps})

    def append_subagent_trace(self, trace: dict[str, Any]) -> None:
        append_jsonl(self.subagent_trace_path, trace)

    def append_llm_trace(self, record: dict[str, Any]) -> None:
        append_jsonl(self.llm_trace_path, record)

    def get_recent_observations(self, *, limit: int = 6) -> list[dict[str, Any]]:
        if not self.react_trace_path.exists():
            return []
        try:
            payload = json.loads(self.react_trace_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        steps = payload.get("steps") if isinstance(payload, dict) else []
        if not isinstance(steps, list):
            return []
        return [step.get("observation", {}) for step in steps[-limit:] if isinstance(step, dict)]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, default=str))
        fh.write("\n")


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        shutil.move(tmp_name, path)
    except Exception:
        Path(tmp_name).unlink(missing_ok=True)
        raise


__all__ = ["TraceStore", "append_jsonl", "atomic_write_json", "now_iso"]
