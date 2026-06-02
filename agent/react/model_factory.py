"""LangChain ChatModel creation and tracing for ReAct agents."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, is_dataclass
from typing import Any, Iterable

from ..llm_gateway import LLMGateway, LLMGatewayConfig
from ..trace_store import TraceStore, now_iso


class LangChainModelFactory:
    """Create ChatModels that support native tool calling."""

    def __init__(
        self,
        *,
        config: LLMGatewayConfig | None = None,
        trace_store: TraceStore | None = None,
        transport: Any | None = None,
    ) -> None:
        self.config = config or LLMGatewayConfig.from_env()
        self.trace_store = trace_store
        self.transport = transport

    @classmethod
    def from_gateway(cls, gateway: LLMGateway, *, trace_store: TraceStore | None = None) -> "LangChainModelFactory":
        return cls(
            config=gateway.config,
            trace_store=trace_store or gateway.trace_store,
            transport=gateway.transport,
        )

    def create_main_model(self, *, model_policy: dict[str, Any] | None = None) -> Any:
        return self._create(caller="main_agent", model_policy=model_policy, mock_context={"kind": "main"})

    def create_subagent_model(self, *, spec: Any, model_policy: dict[str, Any] | None = None) -> Any:
        return self._create(
            caller=str(getattr(spec, "subagent_id", "subagent")),
            model_policy=model_policy or getattr(spec, "model_policy", None),
            mock_context={"kind": "subagent", "spec": spec},
        )

    def _create(self, *, caller: str, model_policy: dict[str, Any] | None, mock_context: dict[str, Any]) -> Any:
        if self.transport is not None and hasattr(self.transport, "bind_tools") and hasattr(self.transport, "invoke"):
            return TracedChatModel(self.transport, trace_store=self.trace_store, caller=caller)

        if self._is_mock_mode():
            return TracedChatModel(
                MockToolCallingChatModel(mock_context=mock_context),
                trace_store=self.trace_store,
                caller=caller,
            )

        policy = dict(model_policy or {})
        model_name = str(policy.get("model") or self.config.model)
        temperature = float(policy.get("temperature", 0.2))
        timeout = float(policy.get("timeout", self.config.timeout))
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:  # pragma: no cover - depends on optional install.
            raise RuntimeError(
                "langchain-openai is required for LangChain-native ReAct mode. "
                "Run `pip install -r requirements-orchestrator.txt`."
            ) from exc

        model = ChatOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            model=model_name,
            temperature=temperature,
            timeout=timeout,
        )
        self.validate_tool_calling(model)
        return TracedChatModel(model, trace_store=self.trace_store, caller=caller)

    def _is_mock_mode(self) -> bool:
        import os

        return os.environ.get("WRITEAGENT_MOCK_LLM") == "1" or not self.config.api_key

    @staticmethod
    def validate_tool_calling(model: Any) -> None:
        if not hasattr(model, "bind_tools"):
            raise RuntimeError("Configured ChatModel does not expose bind_tools(...).")


class TracedChatModel:
    """Small wrapper that preserves the ChatModel bind_tools/invoke surface."""

    def __init__(self, model: Any, *, trace_store: TraceStore | None, caller: str) -> None:
        self.model = model
        self.trace_store = trace_store
        self.caller = caller

    def bind_tools(self, tools: Iterable[Any]) -> "TracedChatModel":
        if not hasattr(self.model, "bind_tools"):
            raise RuntimeError("Configured ChatModel does not expose bind_tools(...).")
        return TracedChatModel(self.model.bind_tools(list(tools)), trace_store=self.trace_store, caller=self.caller)

    def invoke(self, messages: list[Any], config: dict[str, Any] | None = None) -> Any:
        started = time.perf_counter()
        call_id = "llm_" + uuid.uuid4().hex[:12]
        try:
            response = self.model.invoke(messages, config=config)
            self._record(call_id, "ok", started, messages, response=response)
            return response
        except Exception as exc:
            self._record(call_id, "error", started, messages, error=str(exc))
            raise

    def _record(
        self,
        call_id: str,
        status: str,
        started: float,
        messages: list[Any],
        *,
        response: Any | None = None,
        error: str | None = None,
    ) -> None:
        if self.trace_store is None:
            return
        self.trace_store.append_llm_trace(
            {
                "call_id": call_id,
                "caller": self.caller,
                "call_type": "langchain_tool_calling",
                "status": status,
                "model": type(self.model).__name__,
                "started_at": now_iso(),
                "duration_ms": int((time.perf_counter() - started) * 1000),
                "usage": {
                    "prompt_chars": sum(len(_message_content(message)) for message in messages),
                    "completion_chars": len(_message_content(response)) if response is not None else 0,
                },
                "error": error,
            }
        )


class MockToolCallingChatModel:
    """Deterministic offline ChatModel used when no API key is configured."""

    def __init__(self, *, mock_context: dict[str, Any] | None = None, tools: list[Any] | None = None) -> None:
        self.mock_context = mock_context or {"kind": "main"}
        self.tools = tools or []

    def bind_tools(self, tools: Iterable[Any]) -> "MockToolCallingChatModel":
        return MockToolCallingChatModel(mock_context=self.mock_context, tools=list(tools))

    def invoke(self, messages: list[Any], config: dict[str, Any] | None = None) -> Any:
        from langchain_core.messages import AIMessage, ToolMessage

        tool_names = {_tool_name(tool) for tool in self.tools}
        tool_messages = [message for message in messages if isinstance(message, ToolMessage)]
        if self.mock_context.get("kind") == "subagent":
            spec = self.mock_context.get("spec")
            if not tool_messages and "write_intermediate" in tool_names:
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "write_intermediate",
                            "args": {"value": _mock_subagent_payload(spec)},
                            "id": "mock_write_intermediate",
                        }
                    ],
                )
            if "submit_subagent_result" in tool_names:
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "submit_subagent_result",
                            "args": {"status": "completed", "result_summary": f"Mock completed {getattr(spec, 'role', 'subagent')}."},
                            "id": "mock_submit_subagent_result",
                        }
                    ],
                )
            return AIMessage(content="Mock SubAgent completed without tool access.")

        if not tool_messages and "inspect_state" in tool_names:
            return AIMessage(content="", tool_calls=[{"name": "inspect_state", "args": {}, "id": "mock_inspect_state"}])
        return AIMessage(content="Mock run completed. Configure WRITEAGENT_LLM_API_KEY for model-driven orchestration.")


def _tool_name(tool: Any) -> str:
    return str(getattr(tool, "name", ""))


def _message_content(message: Any) -> str:
    if message is None:
        return ""
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content, ensure_ascii=False, default=str)
    except TypeError:
        return str(content)


def _mock_subagent_payload(spec: Any) -> dict[str, Any]:
    output_key = str(getattr(spec, "output_key", ""))
    if output_key.endswith("raw_writing_task"):
        return {
            "topic": "EMI 技术用于 CFRP 损伤检测",
            "paper_type": "survey",
            "language": "zh",
            "target_journal": {"name": "未指定", "level": "未指定"},
            "word_limit": {"total": 8000},
            "core_arguments": ["EMI 技术可作为 CFRP 层合板损伤检测的有效无损监测方法。"],
            "innovation_points": [],
            "research_scope": {"domain": "CFRP structural health monitoring", "subtopics": ["EMI", "damage detection"], "boundary": ""},
            "chapter_framework": [],
            "references_seed": [],
            "missing_info": [],
        }
    if output_key.endswith("raw_outline"):
        return {
            "total_word_budget": 8000,
            "sections": [
                {
                    "id": "1",
                    "title": "引言",
                    "level": 1,
                    "parent_id": None,
                    "key_points": ["研究背景", "问题定义", "论文结构"],
                    "transition_note": "",
                    "word_budget": 1000,
                    "supporting_papers": [],
                }
            ],
        }
    if output_key.endswith("raw_draft"):
        return {
            "abstract": "本文围绕 CFRP 损伤检测展开综述。",
            "keywords": ["CFRP", "EMI", "损伤检测"],
            "sections": [],
            "open_questions": [],
        }
    return {"result_summary": f"Mock output for {getattr(spec, 'role', 'SubAgent')}.", "items": []}


def to_plain_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return value
    return {"value": value}


__all__ = ["LangChainModelFactory", "MockToolCallingChatModel", "TracedChatModel", "to_plain_dict"]
