"""Runtime facade for dynamically derived SubAgents."""

from __future__ import annotations

from pathlib import Path

from ..a2a.types import SubAgentResult, SubAgentSpec
from ..llm_gateway import LLMGateway
from ..react.model_factory import LangChainModelFactory
from ..react.subagent_graph import SubAgentGraphFactory
from ..state_store import StateStore
from ..trace_store import TraceStore


REPO_ROOT = Path(__file__).resolve().parents[2]


class SubAgentRuntime:
    """Execute one SubAgentSpec as an independent LangGraph ReAct agent."""

    def __init__(
        self,
        *,
        llm_gateway: LLMGateway,
        state_store: StateStore | None = None,
        trace_store: TraceStore | None = None,
        repo_root: Path = REPO_ROOT,
    ) -> None:
        self.llm_gateway = llm_gateway
        self.state_store = state_store or StateStore()
        self.trace_store = trace_store
        self.repo_root = Path(repo_root)

    def run(self, spec: SubAgentSpec, state_path: Path) -> SubAgentResult:
        model_factory = LangChainModelFactory.from_gateway(self.llm_gateway, trace_store=self.trace_store)
        return SubAgentGraphFactory(
            model_factory=model_factory,
            state_store=self.state_store,
            trace_store=self.trace_store,
            repo_root=self.repo_root,
        ).run(spec, state_path)


__all__ = ["SubAgentRuntime"]
