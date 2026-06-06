"""Trace event schema."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class TraceEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: uuid4().hex)
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: Literal[
        "model_call", "tool_call", "execute_bash", "artifact_update", "progress_update",
        "delegation", "workflow_gate_blocked", "workflow_gate_allowed"
    ]
    status: str = "ok"
    payload: dict[str, Any] = Field(default_factory=dict)
