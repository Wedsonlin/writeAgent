"""Local ReAct-style Skill scheduler for writeAgent."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .react.prompts import build_mock_action, build_react_messages, build_repair_messages
from .react.skill_registry import SkillRegistry
from .react.state import ReactGraphState
from .react.tools import ReactToolbox, inspect_state
from .react.types import ReactAction, ReactRunResult
from .skill_runner import SkillRunner


VALID_ACTIONS: set[str] = {"run_skill", "inspect_state", "ask_user", "finish"}


class ReactRunner:
    """A JSON-action ReAct scheduler backed by a LangGraph ``StateGraph``."""

    def __init__(
        self,
        *,
        llm_client: Any,
        skill_registry: SkillRegistry,
        skill_runner: SkillRunner,
        max_steps: int = 12,
    ) -> None:
        self.llm_client = llm_client
        self.skill_registry = skill_registry
        self.skill_runner = skill_runner
        self.max_steps = max_steps
        self.tools = ReactToolbox(
            skill_registry=skill_registry,
            skill_runner=skill_runner,
        )

    def run(
        self,
        *,
        user_request: str,
        workspace_root: Path,
        state_path: Path,
    ) -> ReactRunResult:
        """Run the local ReAct dispatcher until a terminal action is reached."""
        workspace_root = Path(workspace_root).resolve()
        state_path = Path(state_path).resolve()
        trace_path = workspace_root / "react_trace.json"
        workspace_root.mkdir(parents=True, exist_ok=True)

        state = _load_state(state_path)
        state.setdefault("case_id", "react-inline")
        state["user_request"] = user_request
        state.setdefault("stage", "init")
        state.setdefault("history", [])
        _write_state(state_path, state)

        graph_input: ReactGraphState = {
            "user_request": user_request,
            "workspace_root": str(workspace_root),
            "state_path": str(state_path),
            "trace_path": str(trace_path),
            "step_count": 0,
            "max_steps": self.max_steps,
            "registry_text": self.skill_registry.render_for_prompt(),
            "steps": [],
            "status": "running",
            "answer": "",
        }
        graph = build_react_graph(self)
        final_state = graph.invoke(
            graph_input,
            config={"recursion_limit": max(self.max_steps * 4 + 10, 25)},
        )
        status = final_state.get("status", "error")
        if status == "running":
            status = "error"
        return ReactRunResult(
            status=status,
            answer=str(final_state.get("answer") or ""),
            state_path=state_path,
            trace_path=trace_path,
            steps=list(final_state.get("steps", [])),
        )

    def decide_action_node(self, state: ReactGraphState) -> dict[str, Any]:
        """Ask the LLM for the next JSON action."""
        state_path = Path(state["state_path"])
        trace_path = Path(state["trace_path"])
        steps = list(state.get("steps", []))
        skill_state = _load_state(state_path)
        state_summary = inspect_state(state_path).get("summary", {})
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
        raw = self._call_llm(messages, mock_response=mock_response)

        try:
            action = parse_react_action(raw)
        except ValueError as first_error:
            try:
                repair_raw = self._call_llm(
                    build_repair_messages(raw, str(first_error)),
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
                _write_trace(trace_path, "error", steps)
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
            "current_action": _action_to_dict(action),
            "raw_output": raw,
            "status": "running",
        }

    def execute_action_node(self, state: ReactGraphState) -> dict[str, Any]:
        """Execute the current ReAct action through the local tool layer."""
        state_path = Path(state["state_path"])
        trace_path = Path(state["trace_path"])
        action_payload = state.get("current_action") or {}
        try:
            action = _action_from_dict(action_payload)
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

        _write_trace(trace_path, status, steps)
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

        if action.action == "ask_user":
            return {
                "tool": "ask_user",
                "status": "ask_user",
                "question": str(action.action_input.get("question") or ""),
            }

        if action.action == "finish":
            return self.tools.finish(str(action.action_input.get("answer") or ""), state_path)

        return {"status": "fatal", "error": f"Unsupported action: {action.action}"}

    def _call_llm(self, messages: list[dict[str, str]], *, mock_response: str) -> str:
        chat_fn = getattr(self.llm_client, "chat", self.llm_client)
        try:
            return chat_fn(
                messages,
                temperature=0.1,
                response_format={"type": "json_object"},
                mock_response=mock_response,
            )
        except TypeError:
            try:
                return chat_fn(
                    messages,
                    temperature=0.1,
                    response_format={"type": "json_object"},
                )
            except TypeError:
                return chat_fn(messages)

    def _mark_state(self, state_path: Path, status: str) -> None:
        state = _load_state(state_path)
        state["last_runner"] = "react"
        state["last_status"] = status
        _write_state(state_path, state)


def build_react_graph(runner: ReactRunner):
    """Build the LangGraph state machine for local ReAct scheduling."""
    try:
        from langgraph.graph import END, START, StateGraph  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "langgraph is required for react mode. "
            "Run `pip install -r requirements-orchestrator.txt`."
        ) from exc

    graph = StateGraph(ReactGraphState)
    graph.add_node("decide_action", runner.decide_action_node)
    graph.add_node("execute_action", runner.execute_action_node)
    graph.add_edge(START, "decide_action")
    graph.add_conditional_edges(
        "decide_action",
        _route_after_decide,
        {
            "execute_action": "execute_action",
            "__end__": END,
        },
    )
    graph.add_conditional_edges(
        "execute_action",
        _route_after_execute,
        {
            "decide_action": "decide_action",
            "__end__": END,
        },
    )
    return graph.compile()


def _route_after_decide(state: ReactGraphState) -> str:
    if state.get("status") == "error":
        return "__end__"
    return "execute_action"


def _route_after_execute(state: ReactGraphState) -> str:
    if state.get("status") == "running":
        return "decide_action"
    return "__end__"


def parse_react_action(raw: str) -> ReactAction:
    """Parse a model response into a validated ``ReactAction``."""
    candidate = _extract_json_candidate(raw)
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON action: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("ReAct action must be a JSON object.")
    action = payload.get("action")
    if action not in VALID_ACTIONS:
        raise ValueError(f"Unsupported ReAct action: {action!r}")
    action_input = payload.get("action_input") or {}
    if not isinstance(action_input, dict):
        raise ValueError("action_input must be a JSON object.")
    return ReactAction(
        thought=str(payload.get("thought") or ""),
        action=action,  # type: ignore[arg-type]
        action_input=action_input,
        raw=raw,
    )


def _action_to_dict(action: ReactAction) -> dict[str, Any]:
    return {
        "thought": action.thought,
        "action": action.action,
        "action_input": action.action_input,
        "raw": action.raw,
    }


def _action_from_dict(payload: dict[str, Any]) -> ReactAction:
    action_name = payload.get("action")
    if action_name not in VALID_ACTIONS:
        raise ValueError(f"Unsupported ReAct action: {action_name!r}")
    action_input = payload.get("action_input") or {}
    if not isinstance(action_input, dict):
        raise ValueError("action_input must be a JSON object.")
    return ReactAction(
        thought=str(payload.get("thought") or ""),
        action=action_name,  # type: ignore[arg-type]
        action_input=action_input,
        raw=str(payload.get("raw") or ""),
    )


def _extract_json_candidate(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text


def _load_state(state_path: Path) -> dict[str, Any]:
    try:
        if not state_path.exists():
            return {}
        data = json.loads(state_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _write_state(state_path: Path, state: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(state_path, state)


def _write_trace(trace_path: Path, status: str, steps: list[dict[str, Any]]) -> None:
    payload = {"status": status, "steps": steps}
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(trace_path, payload)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        shutil.move(tmp, path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise
