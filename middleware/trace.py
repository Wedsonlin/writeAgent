"""Trace middleware marker."""

from __future__ import annotations

from traces.store import TraceStore


class TraceMiddleware:
    name = "writeagent_trace"

    def __init__(self, trace_store: TraceStore) -> None:
        self.trace_store = trace_store

    def record_tool(self, tool_name: str, status: str, payload: dict) -> None:
        self.trace_store.append("tool_call", status=status, payload={"tool": tool_name, **payload})
