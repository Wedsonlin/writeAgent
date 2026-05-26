"""LangGraph state channel for writeAgent.

The state mirrors ``schemas/state.schema.json``. Each cross-node field is wired
to a reducer:

* ``history`` accumulates via list concatenation (``operator.add``).
* Skill-output fields (``writing_task``, ``literature_report`` ...) are overwritten
  by the latest producing node (default LangGraph behaviour).
* ``error`` and ``retry_count`` are managed by the ``retry_with_fallback`` node.

Why ``TypedDict`` rather than ``pydantic.BaseModel``?
    LangGraph's ``StateGraph`` integrates natively with ``TypedDict`` channels.
    Pydantic models are still used at the Skill boundary (``_shared.schemas``) for
    structured validation, but the in-graph representation is a plain dict.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, NotRequired, TypedDict


class HistoryEntry(TypedDict, total=False):
    skill: str
    ts: str
    status: str  # ok | error | skipped
    message: str
    duration_ms: int


class WriteAgentState(TypedDict, total=False):
    """The single channel-set shared by every node in the LangGraph state machine."""

    # --- identity / user input ------------------------------------------------
    case_id: str
    user_request: str

    # --- workflow control -----------------------------------------------------
    stage: str
    history: Annotated[list[HistoryEntry], operator.add]
    error: NotRequired[str]
    retry_count: NotRequired[int]
    next_after_retry: NotRequired[str]  # node id to jump back to

    # --- Skill outputs (latest-wins) -----------------------------------------
    writing_task: NotRequired[dict[str, Any]]          # Skill 1
    literature_report: NotRequired[dict[str, Any]]     # Skill 2
    outline: NotRequired[dict[str, Any]]               # Skill 3
    draft: NotRequired[dict[str, Any]]                 # Skill 4
    formatted_draft: NotRequired[dict[str, Any]]       # Skill 5
    polished_draft: NotRequired[dict[str, Any]]        # Skill 6

    # --- runtime context ------------------------------------------------------
    workspace_root: str   # absolute path of <workspace>/
    state_path: str       # absolute path of <workspace>/state.json
    references_dir: NotRequired[str]


def initial_state(
    *,
    case_id: str,
    user_request: str,
    workspace_root: str,
    state_path: str,
    references_dir: str | None = None,
) -> WriteAgentState:
    """Construct the starting state passed to ``graph.invoke``."""
    base: WriteAgentState = {
        "case_id": case_id,
        "user_request": user_request,
        "stage": "init",
        "history": [],
        "workspace_root": workspace_root,
        "state_path": state_path,
        "retry_count": 0,
    }
    if references_dir:
        base["references_dir"] = references_dir
    return base
