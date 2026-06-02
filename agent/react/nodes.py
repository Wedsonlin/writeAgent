"""LangGraph node functions for the local ReAct Skill scheduler."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..llm_gateway import LLMGateway
from ..skill_runner import SkillRunner
from ..subagents.factory import SubAgentFactory
from ..subagents.runtime import SubAgentRuntime
from ..trace_store import TraceStore
from .actions import action_from_dict, action_to_dict, parse_react_action
from .io import load_state, write_state, write_trace
from .prompts import build_mock_action, build_react_messages, build_repair_messages
from .skill_registry import SkillRegistry
from .state import ReactGraphState
from .tools import ReactToolbox
from .types import ReactAction


class ReactNodes:
    """Stateful ReAct nodes with injected LLM, registry, and tool dependencies."""

    def __init__(
        self,
        *,
        llm_gateway: LLMGateway,
        skill_registry: SkillRegistry,
        skill_runner: SkillRunner,
        subagent_runtime: SubAgentRuntime | None = None,
        subagent_factory: SubAgentFactory | None = None,
        trace_store: TraceStore | None = None,
        max_steps: int = 24,
    ) -> None:
        self.llm_gateway = llm_gateway
        self.skill_registry = skill_registry
        self.max_steps = max_steps
        self.subagent_factory = subagent_factory or SubAgentFactory()
        self.trace_store = trace_store
        self.tools = ReactToolbox(
            skill_registry=skill_registry,
            skill_runner=skill_runner,
            subagent_runtime=subagent_runtime,
        )

    def decide_action_node(self, state: ReactGraphState) -> dict[str, Any]:
        """Ask the LLM for the next JSON action."""
        state_path = Path(state["state_path"])
        trace_path = Path(state["trace_path"])
        steps = list(state.get("steps", []))
        skill_state = load_state(state_path)
        state_summary = self.tools.inspect_state(state_path).get("summary", {})
        messages = build_react_messages(
            user_request=state["user_request"],
            state_summary=state_summary,
            skill_registry_text=state["registry_text"],
            steps=steps,
        )
        mock_response = build_mock_action(
            user_request=state["user_request"],
            state=skill_state,
            registry=self.skill_registry,
            steps=steps,
        )
        raw = self.llm_gateway.chat(
            caller="main_agent",
            messages=messages,
            call_type="main_agent_call",
            temperature=0.1,
            response_format={"type": "json_object"},
            mock_response=mock_response,
        )

        try:
            action = parse_react_action(raw)
        except ValueError as first_error:
            try:
                repair_raw = self.llm_gateway.chat(
                    caller="main_agent",
                    messages=build_repair_messages(raw, str(first_error)),
                    call_type="main_agent_json_repair",
                    temperature=0.0,
                    response_format={"type": "json_object"},
                    mock_response=mock_response,
                )
                action = parse_react_action(repair_raw)
                raw = repair_raw
            except Exception as repair_error:  # noqa: BLE001
                observation = {
                    "status": "error",
                    "error": "Failed to parse ReAct JSON action.",
                    "parse_error": str(first_error),
                    "repair_error": str(repair_error),
                    "raw_output": raw,
                }
                steps.append(
                    {
                        "step": int(state.get("step_count", 0)) + 1,
                        "thought": "",
                        "action": "error",
                        "action_input": {},
                        "observation": observation,
                        "raw": raw,
                    }
                )
                self._write_trace(trace_path, "error", steps)
                self._mark_state(state_path, "error")
                return {
                    "steps": steps,
                    "last_observation": observation,
                    "status": "error",
                    "answer": "LLM action JSON 解析失败，请检查模型输出。",
                    "error": "Failed to parse ReAct JSON action.",
                    "raw_output": raw,
                }

        return {
            "current_action": action_to_dict(action),
            "raw_output": raw,
            "status": "running",
        }

    def execute_action_node(self, state: ReactGraphState) -> dict[str, Any]:
        """Execute the current ReAct action through the local tool layer."""
        state_path = Path(state["state_path"])
        trace_path = Path(state["trace_path"])
        action_payload = state.get("current_action") or {}
        try:
            action = action_from_dict(action_payload)
        except ValueError as exc:
            action = ReactAction(thought="", action="finish", action_input={}, raw="")
            observation = {"status": "fatal", "error": str(exc)}
        else:
            observation = self._execute_action(action, state_path)

        step_count = int(state.get("step_count", 0)) + 1
        step_record = {
            "step": step_count,
            "thought": action.thought,
            "action": action.action,
            "action_input": action.action_input,
            "observation": observation,
            "raw": action.raw or state.get("raw_output", ""),
        }
        steps = [*state.get("steps", []), step_record]
        status = "running"
        answer = str(state.get("answer") or "")

        if action.action == "finish":
            status = "finished"
            answer = str(action.action_input.get("answer") or observation.get("answer") or "")
        elif action.action == "ask_user":
            status = "ask_user"
            answer = str(action.action_input.get("question") or "")
        elif observation.get("status") == "fatal":
            status = "error"
            answer = str(observation.get("error") or "ReAct runner failed.")
        elif step_count >= int(state.get("max_steps", self.max_steps)):
            status = "max_steps_exceeded"
            answer = f"ReAct runner stopped after {state.get('max_steps', self.max_steps)} steps."

        self._write_trace(trace_path, status, steps)
        if status != "running":
            self._mark_state(state_path, status)
        return {
            "step_count": step_count,
            "steps": steps,
            "last_observation": observation,
            "status": status,
            "answer": answer,
        }

    def _execute_action(self, action: ReactAction, state_path: Path) -> dict[str, Any]:
        if action.action == "run_skill":
            skill_name = str(action.action_input.get("skill_name") or "")
            reason = str(action.action_input.get("reason") or action.thought)
            if not skill_name:
                return {"status": "fatal", "error": "run_skill requires action_input.skill_name"}
            return self.tools.run_skill(skill_name, reason, state_path)

        if action.action == "inspect_state":
            return self.tools.inspect_state(state_path)

        if action.action == "delegate_to_subagent":
            spec = self.subagent_factory.from_action_input(action.action_input)
            return self.tools.delegate_to_subagent(spec, state_path)

        if action.action == "ask_user":
            return {
                "tool": "ask_user",
                "status": "ask_user",
                "question": str(action.action_input.get("question") or ""),
            }

        if action.action == "finish":
            return self.tools.finish(str(action.action_input.get("answer") or ""), state_path)

        return {"status": "fatal", "error": f"Unsupported action: {action.action}"}

    def _write_trace(self, trace_path: Path, status: str, steps: list[dict[str, Any]]) -> None:
        if self.trace_store is not None:
            self.trace_store.record_react_trace(status, steps)
        else:
            write_trace(trace_path, status, steps)

    def _mark_state(self, state_path: Path, status: str) -> None:
        state = load_state(state_path)
        state["last_runner"] = "react"
        state["last_status"] = status
        write_state(state_path, state)


def route_after_decide(state: ReactGraphState) -> str:
    if state.get("status") == "error":
        return "__end__"
    return "execute_action"


def route_after_execute(state: ReactGraphState) -> str:
    if state.get("status") == "running":
        return "decide_action"
    return "__end__"


__all__ = ["ReactNodes", "route_after_decide", "route_after_execute"]
