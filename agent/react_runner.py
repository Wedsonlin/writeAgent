"""Local LangChain-native ReAct runner entry point for writeAgent."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .llm_gateway import LLMGateway
from .react.graph import build_graph
from .react.model_factory import LangChainModelFactory
from .react.nodes import ReactNodes
from .react.prompts import MAIN_AGENT_SYSTEM_PROMPT, build_main_user_prompt
from .react.skill_registry import SkillRegistry
from .react.state import MainAgentState
from .react.tools import create_main_tools, inspect_state
from .react.types import ReactRunResult
from .skill_runner import SkillRunner
from .state_store import StateStore, load_state, write_state
from .subagents.factory import SubAgentFactory
from .subagents.runtime import SubAgentRuntime
from .trace_store import TraceStore


class ReactRunner:
    """A LangChain tool-calling ReAct runner backed by LangGraph."""

    def __init__(
        self,
        *,
        llm_gateway: LLMGateway | None = None,
        skill_registry: SkillRegistry,
        skill_runner: SkillRunner,
        max_steps: int = 24,
        model: Any | None = None,
        event_sink: Callable[[dict[str, Any]], None] | None = None,
        human_input_provider: Callable[[str, str], str] | None = None,
    ) -> None:
        self.llm_gateway = llm_gateway
        self.skill_registry = skill_registry
        self.skill_runner = skill_runner
        self.max_steps = max_steps
        self.model = model
        self.event_sink = event_sink
        self.human_input_provider = human_input_provider

    def run(
        self,
        *,
        user_request: str,
        workspace_root: Path,
        state_path: Path,
    ) -> ReactRunResult:
        """Run the Main Agent until it returns a final answer or terminal status."""
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
        except ImportError as exc:  # pragma: no cover - dependency guard.
            raise RuntimeError(
                "langchain-core is required for react mode. "
                "Run `pip install -r requirements-orchestrator.txt`."
            ) from exc

        workspace_root = Path(workspace_root).resolve()
        state_path = Path(state_path).resolve()
        workspace_root.mkdir(parents=True, exist_ok=True)
        trace_store = TraceStore(workspace_root)
        state_store = StateStore()
        llm_gateway = self.llm_gateway or LLMGateway(trace_store=trace_store)
        if getattr(llm_gateway, "trace_store", None) is None:
            llm_gateway.trace_store = trace_store

        state = load_state(state_path)
        state.setdefault("case_id", "react-inline")
        state["user_request"] = user_request
        state.setdefault("stage", "init")
        state.setdefault("history", [])
        write_state(state_path, state)

        subagent_runtime = SubAgentRuntime(
            llm_gateway=llm_gateway,
            state_store=state_store,
            trace_store=trace_store,
            event_sink=self.event_sink,
        )
        tools = create_main_tools(
            skill_registry=self.skill_registry,
            skill_runner=self.skill_runner,
            state_path=state_path,
            subagent_runtime=subagent_runtime,
            subagent_factory=SubAgentFactory(parent_agent_id="main"),
            human_input_provider=self.human_input_provider,
        )
        model = self.model or LangChainModelFactory.from_gateway(llm_gateway, trace_store=trace_store).create_main_model()
        nodes = ReactNodes(
            model=model,
            tools=tools,
            trace_store=trace_store,
            max_steps=self.max_steps,
            event_sink=self.event_sink,
        )
        graph = build_graph(nodes)
        initial_summary = inspect_state(state_path).get("summary", {})
        graph_input: MainAgentState = {
            "user_request": user_request,
            "workspace_root": str(workspace_root),
            "state_path": str(state_path),
            "trace_path": str(trace_store.react_trace_path),
            "agent_id": "main",
            "messages": [
                SystemMessage(content=MAIN_AGENT_SYSTEM_PROMPT),
                HumanMessage(
                    content=build_main_user_prompt(
                        user_request=user_request,
                        state_summary=initial_summary if isinstance(initial_summary, dict) else {},
                        registry_text=self.skill_registry.render_for_prompt(),
                    )
                ),
            ],
            "step_count": 0,
            "max_steps": self.max_steps,
            "registry_text": self.skill_registry.render_for_prompt(),
            "steps": [],
            "status": "running",
            "answer": "",
        }
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
            trace_path=trace_store.react_trace_path,
            steps=list(final_state.get("steps", [])),
        )


__all__ = ["ReactRunner"]
