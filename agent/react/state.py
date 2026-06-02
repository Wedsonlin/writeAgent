"""LangGraph state for the LangChain-native ReAct agents."""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict

try:
    from langgraph.graph.message import add_messages
    from typing_extensions import Annotated
except ImportError:  # pragma: no cover - surfaced when graph is built.
    add_messages = None  # type: ignore[assignment]
    from typing import Annotated  # type: ignore[assignment]


ReactGraphStatus = Literal[
    "running",
    "finished",
    "ask_user",
    "error",
    "max_steps_exceeded",
]


class MainAgentState(TypedDict, total=False):
    """State channels for the Main Agent graph.

    The graph state is separate from the shared Skill ``state.json``. Business
    data still flows through ``state_path``; LangGraph carries messages,
    routing status, and trace records.
    """

    user_request: str
    workspace_root: str
    state_path: str
    trace_path: str
    agent_id: str
    messages: Annotated[list[Any], add_messages]
    step_count: int
    max_steps: int
    registry_text: str
    last_observation: NotRequired[dict[str, Any]]
    status: ReactGraphStatus
    answer: str
    steps: list[dict[str, Any]]
    error: NotRequired[str]


class SubAgentState(TypedDict, total=False):
    """State channels for one delegated SubAgent graph."""

    subagent_id: str
    parent_agent_id: str
    workspace_root: str
    state_path: str
    trace_path: str
    messages: Annotated[list[Any], add_messages]
    step_count: int
    max_steps: int
    status: Literal["running", "completed", "failed", "needs_input", "blocked", "max_steps_exceeded"]
    answer: str
    steps: list[dict[str, Any]]
    last_observation: NotRequired[dict[str, Any]]
    subagent_result: NotRequired[dict[str, Any]]
    error: NotRequired[str]


ReactGraphState = MainAgentState
