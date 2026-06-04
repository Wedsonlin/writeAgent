"""Independent LangGraph ReAct graph for delegated SubAgents."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from ..a2a.types import SubAgentResult, SubAgentSpec, SubAgentTrace
from ..a2a.validator import errors_to_dicts, validate_subagent_spec
from ..state_store import StateStore
from ..trace_store import TraceStore, now_iso
from ..subagents.policy import merged_constraints
from .model_factory import LangChainModelFactory
from .prompts import SUBAGENT_SYSTEM_PROMPT, build_subagent_user_prompt
from .routers import route_after_subagent, route_after_subagent_tools
from .state import SubAgentState
from .subagent_tools import create_subagent_tools


class SubAgentGraphFactory:
    """Create and run a restricted SubAgent ReAct graph for one A2A spec."""

    def __init__(
        self,
        *,
        model_factory: LangChainModelFactory,
        state_store: StateStore | None = None,
        trace_store: TraceStore | None = None,
        repo_root: Path | None = None,
        event_sink: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.model_factory = model_factory
        self.state_store = state_store or StateStore()
        self.trace_store = trace_store
        self.repo_root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
        self.event_sink = event_sink

    def run(self, spec: SubAgentSpec, state_path: Path) -> SubAgentResult:
        started_at = now_iso()
        constraints = merged_constraints(spec)
        spec.constraints = dict(constraints)
        self._emit(
            {
                "type": "subagent_start",
                "subagent_id": spec.subagent_id,
                "parent_agent_id": spec.parent_agent_id,
                "role": spec.role,
                "task": spec.task,
                "input_keys": list(spec.input_keys),
                "file_refs": list(spec.file_refs),
                "output_key": spec.output_key,
            }
        )
        trace = SubAgentTrace(
            subagent_id=spec.subagent_id,
            parent_agent_id=spec.parent_agent_id,
            role=spec.role,
            task=spec.task,
            input_keys=spec.input_keys,
            output_key=spec.output_key,
            skill_context=spec.skill_context,
            prompt_refs=spec.prompt_refs,
            file_refs=spec.file_refs,
            allowed_tools=spec.allowed_tools,
            constraints=spec.constraints,
            status="running",
            started_at=started_at,
        )

        spec_errors = validate_subagent_spec(
            spec,
            workspace_root=self.repo_root,
            file_workspace_root=Path(state_path).parent,
        )
        if spec_errors:
            return self._finish(trace, _failed_result(spec, errors_to_dicts(spec_errors)))

        result_sink: dict[str, Any] = {}
        tools = create_subagent_tools(
            spec=spec,
            state_path=Path(state_path),
            state_store=self.state_store,
            result_sink=result_sink,
        )
        model = self.model_factory.create_subagent_model(spec=spec)
        graph = build_subagent_graph(
            SubAgentNodes(
                model=model,
                tools=tools,
                result_sink=result_sink,
                event_sink=self.event_sink,
                subagent_id=spec.subagent_id,
            )
        )
        state_summary = self.state_store.extract(
            Path(state_path),
            spec.input_keys,
            max_context_chars=int(spec.constraints.get("max_context_chars", 30000)),
        )

        try:
            from langchain_core.messages import HumanMessage, SystemMessage
        except ImportError as exc:  # pragma: no cover - dependency guard.
            raise RuntimeError("langchain-core is required for SubAgent graph execution.") from exc

        graph_input: SubAgentState = {
            "subagent_id": spec.subagent_id,
            "parent_agent_id": spec.parent_agent_id,
            "workspace_root": str(Path(state_path).parent),
            "state_path": str(Path(state_path).resolve()),
            "trace_path": str(self.trace_store.subagent_trace_path if self.trace_store else Path(state_path).with_name("subagent_trace.jsonl")),
            "messages": [
                SystemMessage(content=SUBAGENT_SYSTEM_PROMPT),
                HumanMessage(content=build_subagent_user_prompt(spec=spec, state_summary=state_summary)),
            ],
            "step_count": 0,
            "max_steps": int(spec.constraints.get("max_steps", 3)),
            "status": "running",
            "answer": "",
            "steps": [],
        }
        try:
            final_state = graph.invoke(
                graph_input,
                config={"recursion_limit": max(int(spec.constraints.get("max_steps", 3)) * 4 + 10, 20)},
            )
        except Exception as exc:  # noqa: BLE001 - report protocol failure to Main Agent.
            return self._finish(trace, _failed_result(spec, [{"code": "runtime_error", "message": str(exc), "detail": {}}]))

        result = result_sink.get("result")
        if isinstance(result, SubAgentResult):
            return self._finish(trace, result)

        if final_state.get("status") == "max_steps_exceeded":
            return self._finish(trace, _failed_result(spec, [{"code": "max_steps_exceeded", "message": "SubAgent exceeded max_steps.", "detail": {}}]))
        if final_state.get("status") in {"failed", "blocked"}:
            return self._finish(trace, _failed_result(spec, [{"code": "subagent_failed", "message": str(final_state.get("answer") or "SubAgent failed."), "detail": {}}]))
        return self._finish(trace, _failed_result(spec, [{"code": "missing_submit", "message": "SubAgent ended without submit_subagent_result.", "detail": {}}]))

    def _finish(self, trace: SubAgentTrace, result: SubAgentResult) -> SubAgentResult:
        trace.status = result.status
        trace.ended_at = now_iso()
        trace.result_summary = result.result_summary
        trace.errors = list(result.errors)
        if self.trace_store is not None:
            self.trace_store.append_subagent_trace(asdict(trace))
        self._emit(
            {
                "type": "subagent_end",
                "subagent_id": result.subagent_id,
                "status": result.status,
                "output_key": result.output_key,
                "result_summary": result.result_summary,
                "errors": list(result.errors),
                "artifacts": list(result.artifacts),
            }
        )
        return result

    def _emit(self, event: dict[str, Any]) -> None:
        if self.event_sink is None:
            return
        try:
            self.event_sink(event)
        except Exception:  # noqa: BLE001 - observability must never break the run.
            pass


class SubAgentNodes:
    def __init__(
        self,
        *,
        model: Any,
        tools: list[Any],
        result_sink: dict[str, Any],
        event_sink: Callable[[dict[str, Any]], None] | None = None,
        subagent_id: str = "",
    ) -> None:
        self.bound_model = model.bind_tools(tools)
        self.tool_by_name = {str(getattr(tool, "name", "")): tool for tool in tools}
        self.result_sink = result_sink
        self.event_sink = event_sink
        self.subagent_id = subagent_id

    def subagent_node(self, state: SubAgentState) -> dict[str, Any]:
        try:
            ai_message = self.bound_model.invoke(list(state.get("messages", [])))
        except Exception as exc:  # noqa: BLE001
            return {"status": "failed", "answer": str(exc), "error": str(exc)}

        step_count = int(state.get("step_count", 0))
        self._emit(
            {
                "type": "subagent_reasoning",
                "subagent_id": self.subagent_id,
                "step": step_count + 1,
                "text": _message_text(ai_message),
                "reasoning_content": _reasoning_content(ai_message),
            }
        )

        if not getattr(ai_message, "tool_calls", None):
            return {
                "messages": [ai_message],
                "status": "blocked",
                "answer": "SubAgent returned natural language instead of submit_subagent_result.",
            }
        pending_step = step_count
        for tool_call in list(getattr(ai_message, "tool_calls", None) or []):
            pending_step += 1
            self._emit(
                {
                    "type": "subagent_tool_call",
                    "subagent_id": self.subagent_id,
                    "step": pending_step,
                    "name": str(tool_call.get("name") or ""),
                    "args": dict(tool_call.get("args") or {}),
                }
            )
        return {"messages": [ai_message], "status": "running"}

    def subagent_tools_node(self, state: SubAgentState) -> dict[str, Any]:
        try:
            from langchain_core.messages import ToolMessage
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("langchain-core is required for tool execution.") from exc

        last = (state.get("messages") or [])[-1]
        messages = []
        steps = list(state.get("steps", []))
        step_count = int(state.get("step_count", 0))
        status = "running"
        answer = str(state.get("answer") or "")
        last_observation: dict[str, Any] = {}
        for tool_call in list(getattr(last, "tool_calls", None) or []):
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
                    "type": "subagent_observation",
                    "subagent_id": self.subagent_id,
                    "step": step_count,
                    "name": name,
                    "observation": observation,
                }
            )
            if name == "submit_subagent_result" and "result" in self.result_sink:
                result = self.result_sink["result"]
                status = result.status
                answer = result.result_summary
                break
            if observation.get("status") == "fatal":
                status = "failed"
                answer = str(observation.get("error") or "SubAgent tool execution failed.")
                break
            if step_count >= int(state.get("max_steps", 3)):
                status = "max_steps_exceeded"
                answer = "SubAgent exceeded max_steps."
                break

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
            return json.dumps({"tool": name, "status": "fatal", "error": f"Unauthorized or unknown SubAgent tool: {name}"}, ensure_ascii=False)
        try:
            result = tool.invoke(args)
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
            if name == "write_intermediate" and ("valid dictionary" in error or "dict_type" in error):
                return json.dumps(
                    {
                        "tool": name,
                        "status": "fatal",
                        "error": (
                            "write_intermediate.value must be a JSON object; "
                            "wrap arrays under the schema key such as papers/claims/items."
                        ),
                    },
                    ensure_ascii=False,
                )
            return json.dumps({"tool": name, "status": "fatal", "error": str(exc)}, ensure_ascii=False)
        return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)

    def _emit(self, event: dict[str, Any]) -> None:
        if self.event_sink is None:
            return
        try:
            self.event_sink(event)
        except Exception:  # noqa: BLE001 - observability must never break the run.
            pass


def build_subagent_graph(nodes: SubAgentNodes):
    try:
        from langgraph.graph import END, START, StateGraph  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "langgraph is required for react mode. "
            "Run `pip install -r requirements-orchestrator.txt`."
        ) from exc

    graph = StateGraph(SubAgentState)
    graph.add_node("subagent", nodes.subagent_node)
    graph.add_node("subagent_tools", nodes.subagent_tools_node)
    graph.add_edge(START, "subagent")
    graph.add_conditional_edges(
        "subagent",
        route_after_subagent,
        {"subagent_tools": "subagent_tools", "__end__": END},
    )
    graph.add_conditional_edges(
        "subagent_tools",
        route_after_subagent_tools,
        {"subagent": "subagent", "__end__": END},
    )
    return graph.compile()


def _failed_result(spec: SubAgentSpec, errors: list[dict[str, Any]]) -> SubAgentResult:
    return SubAgentResult(
        subagent_id=spec.subagent_id,
        parent_agent_id=spec.parent_agent_id,
        status="failed",
        output_key=None,
        result_summary="Sub-agent execution failed.",
        errors=errors,
    )


def _parse_json_observation(text: str) -> dict[str, Any]:
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        return {"status": "ok", "text": text}
    return loaded if isinstance(loaded, dict) else {"status": "ok", "value": loaded}


def _message_text(message: Any) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content, ensure_ascii=False, default=str)
    except TypeError:
        return str(content)


def _reasoning_content(message: Any) -> str:
    kwargs = getattr(message, "additional_kwargs", None)
    if isinstance(kwargs, dict):
        value = kwargs.get("reasoning_content") or kwargs.get("reasoning")
        if value:
            return str(value)
    return ""


__all__ = ["SubAgentGraphFactory", "SubAgentNodes", "build_subagent_graph"]
