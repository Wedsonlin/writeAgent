"""LangGraph state for the local ReAct Skill scheduler."""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict


ReactGraphStatus = Literal[
    "running",
    "finished",
    "ask_user",
    "error",
    "max_steps_exceeded",
]


class ReactGraphState(TypedDict, total=False):
    """State channels for the ReAct ``StateGraph``.

    The graph state is separate from the shared Skill ``state.json``. It stores
    orchestration-only fields such as the current action and trace steps, while
    Skills continue to exchange business data through ``state_path``.
    """

    user_request: str
    workspace_root: str
    state_path: str
    trace_path: str
    step_count: int
    max_steps: int
    registry_text: str
    steps: list[dict[str, Any]]
    raw_output: NotRequired[str]
    current_action: NotRequired[dict[str, Any]]
    last_observation: NotRequired[dict[str, Any]]
    status: ReactGraphStatus
    answer: str
    error: NotRequired[str]
