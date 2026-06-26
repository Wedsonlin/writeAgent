"""Ambient per-run context for tool execution.

LangGraph exposes request context to middleware, but not every StructuredTool
call receives a ``ToolRuntime`` parameter. This module lets middleware bridge
that context to tool wrappers without exposing project fields in tool schemas.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator


_CURRENT_RUNTIME_CONTEXT: ContextVar[Any | None] = ContextVar("writeagent_runtime_context", default=None)


@contextmanager
def use_runtime_context(context: Any | None) -> Iterator[None]:
    token = _CURRENT_RUNTIME_CONTEXT.set(context)
    try:
        yield
    finally:
        _CURRENT_RUNTIME_CONTEXT.reset(token)


def current_runtime_context_value(key: str) -> Any:
    context = _CURRENT_RUNTIME_CONTEXT.get()
    if isinstance(context, dict):
        return context.get(key)
    return getattr(context, key, None)
