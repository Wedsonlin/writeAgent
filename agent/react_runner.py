"""Local ReAct-style Skill scheduler entry point for writeAgent."""

from __future__ import annotations

from pathlib import Path

from .llm_gateway import LLMGateway
from .react.graph import build_graph
from .react.io import load_state, write_state
from .react.nodes import ReactNodes
from .react.skill_registry import SkillRegistry
from .react.state import ReactGraphState
from .react.types import ReactRunResult
from .skill_runner import SkillRunner
from .state_store import StateStore
from .subagents.factory import SubAgentFactory
from .subagents.runtime import SubAgentRuntime
from .trace_store import TraceStore


class ReactRunner:
    """A JSON-action ReAct scheduler backed by a LangGraph ``StateGraph``."""

    def __init__(
        self,
        *,
        llm_gateway: LLMGateway | None = None,
        skill_registry: SkillRegistry,
        skill_runner: SkillRunner,
        max_steps: int = 24,
    ) -> None:
        self.llm_gateway = llm_gateway
        self.skill_registry = skill_registry
        self.skill_runner = skill_runner
        self.max_steps = max_steps

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
        trace_store = TraceStore(workspace_root)
        trace_path = trace_store.react_trace_path
        state_store = StateStore()
        llm_gateway = self.llm_gateway or LLMGateway(trace_store=trace_store)
        if getattr(llm_gateway, "trace_store", None) is None:
            llm_gateway.trace_store = trace_store
        subagent_runtime = SubAgentRuntime(
            llm_gateway=llm_gateway,
            state_store=state_store,
            trace_store=trace_store,
        )
        workspace_root.mkdir(parents=True, exist_ok=True)

        state = load_state(state_path)
        state.setdefault("case_id", "react-inline")
        state["user_request"] = user_request
        state.setdefault("stage", "init")
        state.setdefault("history", [])
        write_state(state_path, state)

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
        nodes = ReactNodes(
            llm_gateway=llm_gateway,
            skill_registry=self.skill_registry,
            skill_runner=self.skill_runner,
            subagent_runtime=subagent_runtime,
            subagent_factory=SubAgentFactory(parent_agent_id="main"),
            trace_store=trace_store,
            max_steps=self.max_steps,
        )
        graph = build_graph(nodes)
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


__all__ = ["ReactRunner"]
