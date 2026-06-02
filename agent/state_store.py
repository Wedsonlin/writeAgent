"""Shared state.json helpers for workflow, ReAct, and Sub-agents."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


FORMAL_OUTPUT_KEYS = {
    "writing_task",
    "literature_report",
    "outline",
    "draft",
    "formatted_draft",
    "polished_draft",
}


class StateStore:
    """Load, summarize, and safely update writeAgent state files."""

    def load(self, state_path: Path) -> dict[str, Any]:
        return load_state(state_path)

    def save(self, state_path: Path, state: dict[str, Any]) -> None:
        write_state(state_path, state)

    def summarize(self, state_path: Path, *, max_text: int = 600) -> dict[str, Any]:
        return summarize_state(load_state(state_path), max_text=max_text)

    def extract(self, state_path: Path, keys: list[str], *, max_context_chars: int | None = None) -> dict[str, Any]:
        state = load_state(state_path)
        extracted = {key: get_path(state, key) for key in keys if get_path(state, key) is not MISSING}
        if max_context_chars is not None:
            return trim_context(extracted, max_context_chars)
        return extracted

    def write_intermediate(self, state_path: Path, output_key: str, value: Any) -> None:
        state = load_state(state_path)
        write_intermediate(state, output_key, value)
        write_state(state_path, state)


MISSING = object()


def load_state(state_path: Path) -> dict[str, Any]:
    path = Path(state_path)
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}
    except json.JSONDecodeError:
        return {}


def write_state(state_path: Path, state: dict[str, Any]) -> None:
    path = Path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, ensure_ascii=False, indent=2)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        shutil.move(tmp_name, path)
    except Exception:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def get_path(root: dict[str, Any], dotted_path: str) -> Any:
    current: Any = root
    for part in dotted_path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return MISSING
    return current


def set_path(root: dict[str, Any], dotted_path: str, value: Any) -> None:
    parts = dotted_path.split(".")
    current: dict[str, Any] = root
    for part in parts[:-1]:
        child = current.setdefault(part, {})
        if not isinstance(child, dict):
            raise ValueError(f"Cannot set nested path through non-object field: {part}")
        current = child
    current[parts[-1]] = value


def write_intermediate(state: dict[str, Any], output_key: str, value: Any) -> None:
    if not output_key.startswith("intermediate."):
        raise ValueError(f"Sub-agent output_key must start with 'intermediate.': {output_key}")
    if output_key.split(".", 1)[0] in FORMAL_OUTPUT_KEYS:
        raise ValueError(f"Sub-agent cannot write formal output key: {output_key}")
    set_path(state, output_key, value)


def summarize_state(state: dict[str, Any], *, max_text: int = 600) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    preferred = [
        "user_request",
        "stage",
        "history",
        "intermediate",
        "writing_task",
        "literature_report",
        "outline",
        "draft",
        "formatted_draft",
        "polished_draft",
        "last_runner",
        "last_status",
    ]
    for key in preferred:
        if key in state:
            summary[key] = summarize_value(state[key], max_text=max_text)
    for key in sorted(state):
        if key not in summary and not key.startswith("_"):
            summary[key] = summarize_value(state[key], max_text=max_text)
    return summary


def summarize_value(value: Any, *, max_text: int = 600, depth: int = 0) -> Any:
    if isinstance(value, str):
        return value if len(value) <= max_text else {"type": "str", "length": len(value), "preview": value[:max_text]}
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return {
            "type": "list",
            "length": len(value),
            "items": [summarize_value(item, max_text=max_text, depth=depth + 1) for item in value[:5]],
        }
    if isinstance(value, dict):
        if depth >= 2:
            return {"type": "dict", "keys": sorted(str(key) for key in value)}
        result: dict[str, Any] = {"type": "dict", "keys": sorted(str(key) for key in value)}
        for key in list(value)[:8]:
            result[str(key)] = summarize_value(value[key], max_text=max_text, depth=depth + 1)
        return result
    return {"type": type(value).__name__, "repr": repr(value)[:max_text]}


def trim_context(value: dict[str, Any], max_chars: int) -> dict[str, Any]:
    text = json.dumps(value, ensure_ascii=False)
    if len(text) <= max_chars:
        return value
    return {
        "_truncated": True,
        "_max_context_chars": max_chars,
        "summary": summarize_value(value, max_text=max(200, max_chars // 4)),
    }


__all__ = [
    "FORMAL_OUTPUT_KEYS",
    "MISSING",
    "StateStore",
    "get_path",
    "load_state",
    "set_path",
    "summarize_state",
    "summarize_value",
    "trim_context",
    "write_intermediate",
    "write_state",
]
