"""Conditional routing helpers for LangGraph ReAct graphs."""

from __future__ import annotations

from typing import Any


def route_after_main_agent(state: dict[str, Any]) -> str:
    if state.get("status") not in (None, "running"):
        return "__end__"
    last = _last_message(state)
    if getattr(last, "tool_calls", None):
        return "main_tools"
    return "__end__"


def route_after_main_tools(state: dict[str, Any]) -> str:
    if state.get("status") == "running":
        return "main_agent"
    return "__end__"


def route_after_subagent(state: dict[str, Any]) -> str:
    if state.get("status") not in (None, "running"):
        return "__end__"
    last = _last_message(state)
    if getattr(last, "tool_calls", None):
        return "subagent_tools"
    return "__end__"


def route_after_subagent_tools(state: dict[str, Any]) -> str:
    if state.get("status") == "running":
        return "subagent"
    return "__end__"


def _last_message(state: dict[str, Any]) -> Any | None:
    messages = state.get("messages") or []
    return messages[-1] if messages else None


__all__ = [
    "route_after_main_agent",
    "route_after_main_tools",
    "route_after_subagent",
    "route_after_subagent_tools",
]
