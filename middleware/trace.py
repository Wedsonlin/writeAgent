"""Trace middleware for tool execution."""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable
from langchain.agents.middleware import AgentMiddleware, ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.errors import GraphBubbleUp
from langgraph.types import Command
from agent_core.config import RuntimeConfig
from agent_core.run_context import use_runtime_context
from traces.store import TraceStore


class TraceMiddleware(AgentMiddleware):
    name = "writeagent_trace"

    def __init__(self, trace_store: TraceStore, *, runtime_config: RuntimeConfig | None = None) -> None:
        self.trace_store = trace_store
        self.runtime_config = runtime_config

    def record_tool(self, tool_name: str, status: str, payload: dict, request: ToolCallRequest | None = None) -> None:
        self._trace_store_for_request(request).append("tool_call", status=status, payload={"tool": tool_name, **payload})

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        tool_name = request.tool_call["name"]
        args = request.tool_call["args"]
        try:
            with use_runtime_context(_request_context(request)):
                result = handler(request)
        except GraphBubbleUp:
            raise
        except Exception as exc:
            self.record_tool(
                tool_name,
                "failed",
                {
                    "args": args,
                    "error": str(exc),
                    "error_type": exc.__class__.__name__,
                },
                request,
            )
            return ToolMessage(
                content=f"Tool '{tool_name}' failed: {exc}",
                tool_call_id=request.tool_call["id"],
            )

        self.record_tool(tool_name, "success", {"args": args, "result": _serialize_result(result)}, request)
        return result

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        tool_name = request.tool_call["name"]
        args = request.tool_call["args"]
        try:
            with use_runtime_context(_request_context(request)):
                result = await handler(request)
        except GraphBubbleUp:
            raise
        except Exception as exc:
            await asyncio.to_thread(
                self.record_tool,
                tool_name,
                "failed",
                {
                    "args": args,
                    "error": str(exc),
                    "error_type": exc.__class__.__name__,
                },
                request,
            )
            return ToolMessage(
                content=f"Tool '{tool_name}' failed: {exc}",
                tool_call_id=request.tool_call["id"],
            )

        await asyncio.to_thread(
            self.record_tool,
            tool_name,
            "success",
            {"args": args, "result": _serialize_result(result)},
            request,
        )
        return result

    def _trace_store_for_request(self, request: ToolCallRequest | None) -> TraceStore:
        if self.runtime_config is None or request is None:
            return self.trace_store
        project_id = _request_context_value(request, "project_id")
        if not isinstance(project_id, str) or not project_id.strip():
            return self.trace_store
        project_cfg = self.runtime_config.for_project(project_id)
        project_cfg.ensure_dirs()
        if project_cfg.trace_path == self.trace_store.path:
            return self.trace_store
        return TraceStore(project_cfg.trace_path)


def _serialize_result(result: Any) -> Any:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if hasattr(result, "dict"):
        return result.dict()
    if isinstance(result, (str, int, float, bool, list, tuple, dict)) or result is None:
        return result
    return repr(result)


def _request_context_value(request: ToolCallRequest, key: str) -> Any:
    context = _request_context(request)
    if isinstance(context, dict):
        return context.get(key)
    return getattr(context, key, None)


def _request_context(request: ToolCallRequest) -> Any:
    runtime = getattr(request, "runtime", None)
    return getattr(runtime, "context", None)
