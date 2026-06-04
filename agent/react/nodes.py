"""LangGraph node functions for LangChain-native ReAct orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from ..state_store import load_state, write_state
from ..trace_store import TraceStore
from .state import MainAgentState


class ReactNodes:
    """Stateful Main Agent nodes backed by ChatModel tool-calling."""

    def __init__(
        self,
        *,
        model: Any,
        tools: list[Any],
        trace_store: TraceStore | None = None,
        max_steps: int = 24,
        event_sink: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.model = model
        self.tools = tools
        self.tool_by_name = {str(getattr(tool, "name", "")): tool for tool in tools}
        self.bound_model = model.bind_tools(tools)
        self.trace_store = trace_store
        self.max_steps = max_steps
        self.event_sink = event_sink

    def main_agent_node(self, state: MainAgentState) -> dict[str, Any]:
        """Ask the bound ChatModel for either tool calls or a final answer."""
        try:
            ai_message = self.bound_model.invoke(list(state.get("messages", [])))
        except Exception as exc:  # noqa: BLE001 - return structured graph failure.
            self._write_trace(state, "error", list(state.get("steps", [])))
            self._mark_state(Path(state["state_path"]), "error")
            return {"status": "error", "answer": str(exc), "error": str(exc)}

        step_count = int(state.get("step_count", 0))
        self._emit(
            {
                "type": "reasoning",
                "agent": "main",
                "step": step_count + 1,
                "text": _message_text(ai_message),
                "reasoning_content": _reasoning_content(ai_message),
            }
        )

        status = "running"
        answer = str(state.get("answer") or "")
        if not getattr(ai_message, "tool_calls", None):
            status = "finished"
            answer = _message_text(ai_message)
            self._write_trace(state, status, list(state.get("steps", [])))
            self._mark_state(Path(state["state_path"]), status)
        else:
            pending_step = step_count
            for tool_call in list(getattr(ai_message, "tool_calls", None) or []):
                pending_step += 1
                self._emit(
                    {
                        "type": "tool_call",
                        "agent": "main",
                        "step": pending_step,
                        "name": str(tool_call.get("name") or ""),
                        "args": dict(tool_call.get("args") or {}),
                    }
                )

        return {"messages": [ai_message], "status": status, "answer": answer}

    def main_tools_node(self, state: MainAgentState) -> dict[str, Any]:
        """Execute tool calls emitted by the last AIMessage."""
        try:
            from langchain_core.messages import ToolMessage
        except ImportError as exc:  # pragma: no cover - dependency guard.
            raise RuntimeError("langchain-core is required for tool execution.") from exc

        last = (state.get("messages") or [])[-1]
        tool_calls = list(getattr(last, "tool_calls", None) or [])
        messages = []
        steps = list(state.get("steps", []))
        step_count = int(state.get("step_count", 0))
        status = "running"
        answer = str(state.get("answer") or "")
        last_observation: dict[str, Any] = {}

        """
        tool_calls=[
            {"name": "inspect_state", "args": {}, "id": "call_1"},
            {"name": "run_skill", "args": {"skill_name": "...", "reason": "..."}, "id": "call_2"},
        ]
        """
        for tool_call in tool_calls:
            name = str(tool_call.get("name") or "")
            args = dict(tool_call.get("args") or {})
            call_id = str(tool_call.get("id") or f"call_{step_count + 1}")
            observation_text = self._invoke_tool(name, args)
            observation = _parse_json_observation(observation_text)
            last_observation = observation
            step_count += 1
            steps.append(
                {
                    "step": step_count,
                    "action": name,
                    "action_input": args,
                    "observation": observation,
                    "tool_call_id": call_id,
                }
            )
            messages.append(ToolMessage(content=observation_text, tool_call_id=call_id, name=name))
            self._emit(
                {
                    "type": "observation",
                    "agent": "main",
                    "step": step_count,
                    "name": name,
                    "observation": observation,
                }
            )

            if observation.get("status") == "ask_user":
                status = "ask_user"
                answer = str(observation.get("question") or "")
                break
            if observation.get("status") == "fatal":
                status = "error"
                answer = str(observation.get("error") or "ReAct tool execution failed.")
                break
            if step_count >= int(state.get("max_steps", self.max_steps)):
                status = "max_steps_exceeded"
                answer = f"ReAct runner stopped after {state.get('max_steps', self.max_steps)} steps."
                break

        self._write_trace(state, status, steps)
        if status != "running":
            self._mark_state(Path(state["state_path"]), status)
        return {
            "messages": messages,
            "step_count": step_count,
            "steps": steps,
            "last_observation": last_observation,
            "status": status,
            "answer": answer,
        }

    def _invoke_tool(self, name: str, args: dict[str, Any]) -> str:
        tool = self.tool_by_name.get(name)
        if tool is None:
            return json.dumps({"tool": name, "status": "fatal", "error": f"Unknown tool: {name}"}, ensure_ascii=False)
        try:
            result = tool.invoke(args)
        except Exception as exc:  # noqa: BLE001 - return as tool observation for the model/trace.
            return json.dumps({"tool": name, "status": "fatal", "error": str(exc)}, ensure_ascii=False)
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False, default=str)

    def _write_trace(self, state: MainAgentState, status: str, steps: list[dict[str, Any]]) -> None:
        if self.trace_store is not None:
            self.trace_store.record_react_trace(status, steps)
            return
        trace_path = Path(state["trace_path"])
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        trace_path.write_text(json.dumps({"status": status, "steps": steps}, ensure_ascii=False, indent=2), encoding="utf-8")

    def _mark_state(self, state_path: Path, status: str) -> None:
        state = load_state(state_path)
        state["last_runner"] = "langchain-react"
        state["last_status"] = status
        write_state(state_path, state)

    def _emit(self, event: dict[str, Any]) -> None:
        if self.event_sink is None:
            return
        try:
            self.event_sink(event)
        except Exception:  # noqa: BLE001 - observability must never break the run.
            pass


def _reasoning_content(message: Any) -> str:
    """Extract provider-specific chain-of-thought (e.g. DeepSeek-R1) if present."""
    kwargs = getattr(message, "additional_kwargs", None)
    if isinstance(kwargs, dict):
        value = kwargs.get("reasoning_content") or kwargs.get("reasoning")
        if value:
            return str(value)
    return ""


def _message_text(message: Any) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content, ensure_ascii=False, default=str)
    except TypeError:
        return str(content)


def _parse_json_observation(text: str) -> dict[str, Any]:
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        return {"status": "ok", "text": text}
    return loaded if isinstance(loaded, dict) else {"status": "ok", "value": loaded}


__all__ = ["ReactNodes"]
