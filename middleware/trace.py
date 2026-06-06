"""Trace middleware for tool execution."""

from __future__ import annotations

from typing import Any, Callable
from langchain.agents.middleware import AgentMiddleware, ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from traces.store import TraceStore


class TraceMiddleware(AgentMiddleware):
    name = "writeagent_trace"

    def __init__(self, trace_store: TraceStore) -> None:
        self.trace_store = trace_store

    def record_tool(self, tool_name: str, status: str, payload: dict) -> None:
        self.trace_store.append("tool_call", status=status, payload={"tool": tool_name, **payload})

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        tool_name = request.tool_call["name"]
        args = request.tool_call["args"]
        try:
            result = handler(request)
        except Exception as exc:
            self.record_tool(
                tool_name,
                "failed",
                {
                    "args": args,
                    "error": str(exc),
                    "error_type": exc.__class__.__name__,
                },
            )
            return ToolMessage(
                content=f"Tool '{tool_name}' failed: {exc}",
                tool_call_id=request.tool_call["id"],
            )

        self.record_tool(tool_name, "success", {"args": args, "result": _serialize_result(result)})
        return result


def _serialize_result(result: Any) -> Any:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if hasattr(result, "dict"):
        return result.dict()
    if isinstance(result, (str, int, float, bool, list, tuple, dict)) or result is None:
        return result
    return repr(result)
