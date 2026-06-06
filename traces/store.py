"""Append-only local trace store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema import TraceEvent


class TraceStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event_type: str, *, status: str = "ok", payload: dict[str, Any] | None = None) -> TraceEvent:
        event = TraceEvent(event_type=event_type, status=status, payload=payload or {})
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(event.model_dump_json() + "\n")
        return event

    def read_all(self) -> list[TraceEvent]:
        if not self.path.exists():
            return []
        events: list[TraceEvent] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(TraceEvent.model_validate(json.loads(line)))
        return events
