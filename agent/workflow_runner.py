"""Thin wrapper around the fixed LangGraph workflow mode."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .workflow.checkpointer import export_state_json, make_checkpointer
from .workflow.graph import build_graph
from .workflow.state import initial_state


@dataclass
class WorkflowRunResult:
    case_id: str
    thread_id: str
    workspace_root: Path
    state_path: Path
    final_state: dict[str, Any]


class WorkflowRunner:
    """Execute the existing fixed LangGraph Skill pipeline."""

    def run(
        self,
        *,
        case_id: str,
        user_request: str,
        workspace_root: Path,
        references_dir: str | None,
        thread_id: str,
        include_optional_skills: bool,
    ) -> WorkflowRunResult:
        workspace_root = Path(workspace_root).resolve()
        state_path = workspace_root / "state.json"
        init = initial_state(
            case_id=case_id,
            user_request=user_request,
            workspace_root=str(workspace_root),
            state_path=str(state_path),
            references_dir=references_dir,
        )
        export_state_json(workspace_root, dict(init))

        checkpointer = make_checkpointer(workspace_root)
        graph = build_graph(
            checkpointer=checkpointer,
            include_optional_skills=include_optional_skills,
        )
        final_state = graph.invoke(
            init,
            config={"configurable": {"thread_id": thread_id}},
        )
        export_state_json(workspace_root, final_state)
        return WorkflowRunResult(
            case_id=case_id,
            thread_id=thread_id,
            workspace_root=workspace_root,
            state_path=state_path,
            final_state=dict(final_state),
        )
