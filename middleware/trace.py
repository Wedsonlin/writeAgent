"""Trace middleware for tool execution."""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable
from langchain.agents.middleware import AgentMiddleware, ToolCallRequest
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import ToolMessage
from langgraph.errors import GraphBubbleUp
from langgraph.types import Command
from agent_core.config import RuntimeConfig
from agent_core.run_context import use_runtime_context
from traces.store import TraceStore


class TraceMiddleware(AgentMiddleware):
    name = "writeagent_trace"

    def __init__(
        self,
        trace_store: TraceStore,
        *,
        runtime_config: RuntimeConfig | None = None,
        agent_scope: str = "root",
        agent_name: str = "writeAgent",
    ) -> None:
        self.trace_store = trace_store
        self.runtime_config = runtime_config
        self.agent_scope = agent_scope
        self.agent_name = agent_name

    def record_tool(self, tool_name: str, status: str, payload: dict, request: ToolCallRequest | None = None) -> None:
        self._trace_store_for_request(request).append(
            "tool_call",
            status=status,
            payload=self._scoped_payload({"tool": tool_name, **payload}),
        )

    def record_model(self, status: str, payload: dict, request: ModelRequest | Any | None = None) -> None:
        self._trace_store_for_request(request).append(
            "model_call",
            status=status,
            payload=self._scoped_payload(payload),
        )

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
        except GraphBubbleUp as exc:
            self.record_tool(
                tool_name,
                "interrupted",
                {
                    "args": args,
                    "error": str(exc),
                    "error_type": exc.__class__.__name__,
                },
                request,
            )
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
        except GraphBubbleUp as exc:
            await asyncio.to_thread(
                self.record_tool,
                tool_name,
                "interrupted",
                {
                    "args": args,
                    "error": str(exc),
                    "error_type": exc.__class__.__name__,
                },
                request,
            )
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

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        try:
            response = handler(request)
        except GraphBubbleUp as exc:
            self.record_model("interrupted", _model_error_payload(request, exc), request)
            raise
        except Exception as exc:
            self.record_model("failed", _model_error_payload(request, exc), request)
            raise

        self.record_model("success", _model_payload(request, response), request)
        return response

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        try:
            response = await handler(request)
        except GraphBubbleUp as exc:
            await asyncio.to_thread(self.record_model, "interrupted", _model_error_payload(request, exc), request)
            raise
        except Exception as exc:
            await asyncio.to_thread(self.record_model, "failed", _model_error_payload(request, exc), request)
            raise

        await asyncio.to_thread(self.record_model, "success", _model_payload(request, response), request)
        return response

    def _trace_store_for_request(self, request: Any | None) -> TraceStore:
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

    def _scoped_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "agent_scope": self.agent_scope,
            "agent_name": self.agent_name,
            **payload,
        }


def _serialize_result(result: Any) -> Any:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if hasattr(result, "dict"):
        return result.dict()
    if isinstance(result, (str, int, float, bool, list, tuple, dict)) or result is None:
        return result
    return repr(result)


def _model_payload(request: Any, response: Any) -> dict[str, Any]:
    return {
        "model": _model_name(request),
        "message_count": _message_count(request),
        "tool_calls": _tool_call_names(response),
    }


def _model_error_payload(request: Any, exc: BaseException) -> dict[str, Any]:
    return {
        "model": _model_name(request),
        "message_count": _message_count(request),
        "error": str(exc),
        "error_type": exc.__class__.__name__,
    }


def _model_name(request: Any) -> str | None:
    model = getattr(request, "model", None)
    if model is None:
        return None
    if isinstance(model, str):
        return model
    for attr in ("model_name", "model", "name"):
        value = getattr(model, attr, None)
        if isinstance(value, str) and value:
            return value
    return model.__class__.__name__


def _message_count(request: Any) -> int:
    messages = getattr(request, "messages", None)
    if messages is None:
        state = getattr(request, "state", None)
        if isinstance(state, dict):
            messages = state.get("messages")
    return len(messages) if isinstance(messages, list) else 0


def _tool_call_names(response: Any) -> list[str]:
    names: list[str] = []
    for message in getattr(response, "result", []) or []:
        tool_calls = getattr(message, "tool_calls", None)
        if not tool_calls:
            additional_kwargs = getattr(message, "additional_kwargs", None)
            if isinstance(additional_kwargs, dict):
                tool_calls = additional_kwargs.get("tool_calls")
        if not isinstance(tool_calls, list):
            continue
        for call in tool_calls:
            name = _tool_call_name(call)
            if name:
                names.append(name)
    return names


def _tool_call_name(call: Any) -> str | None:
    if not isinstance(call, dict):
        return None
    name = call.get("name")
    if isinstance(name, str) and name:
        return name
    function = call.get("function")
    if isinstance(function, dict) and isinstance(function.get("name"), str):
        return function["name"]
    return None


def _request_context_value(request: Any, key: str) -> Any:
    context = _request_context(request)
    if isinstance(context, dict):
        return context.get(key)
    return getattr(context, key, None)


def _request_context(request: Any) -> Any:
    runtime = getattr(request, "runtime", None)
    return getattr(runtime, "context", None)
