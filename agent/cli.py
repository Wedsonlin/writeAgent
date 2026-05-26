"""writeAgent CLI — ``python -m agent`` / ``writeagent`` entry point.

Sub-commands
------------
- ``run``     Kick off a fresh pipeline from a user-request file or string.
- ``resume``  Continue from the latest checkpoint of an existing thread.
- ``inspect`` Pretty-print the current ``state.json``.

All three commands route to the *same* compiled graph defined in
:mod:`agent.graph` and respect the same workspace layout.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Optional

try:
    import typer
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "typer is not installed. Run `pip install -r requirements-orchestrator.txt`."
    ) from exc

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from .checkpointer import export_state_json, make_checkpointer
from .graph import build_graph
from .state import initial_state


app = typer.Typer(help="writeAgent — LangGraph 编排的论文写作 Agent CLI")
console = Console()


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORKSPACE = REPO_ROOT / ".writeagent"


def _ensure_workspace(workspace: Optional[Path]) -> Path:
    ws = workspace or DEFAULT_WORKSPACE
    ws.mkdir(parents=True, exist_ok=True)
    # Always operate on an absolute path so subprocesses started under a
    # different cwd (skill_runner sets cwd=skill_dir) still resolve correctly.
    return ws.resolve()


def _read_request(case: Optional[Path], request: Optional[str]) -> tuple[str, str]:
    """Resolve (case_id, user_request) from either a file or an inline string."""
    if case is not None:
        text = case.read_text(encoding="utf-8")
        stem = case.stem
        case_id = stem.replace("00-", "").replace(" ", "-") or "case-" + uuid.uuid4().hex[:6]
        return case_id, text
    if request:
        return "inline-" + uuid.uuid4().hex[:6], request
    raise typer.BadParameter("Provide either --case <file> or --request <text>.")


# --------------------------------------------------------------------------- #
# run
# --------------------------------------------------------------------------- #


@app.command()
def run(
    case: Optional[Path] = typer.Option(
        None, "--case", "-c", exists=True, file_okay=True, dir_okay=False,
        help="包含用户原始需求的 Markdown / 文本文件。",
    ),
    request: Optional[str] = typer.Option(
        None, "--request", "-r", help="直接以字符串形式提供的用户需求。"
    ),
    workspace: Optional[Path] = typer.Option(
        None, "--workspace", "-w", help="工作目录（默认 ./.writeagent）。"
    ),
    references: Optional[Path] = typer.Option(
        None, "--references", help="参考文献目录（含 .bib / .pdf）。"
    ),
    thread_id: Optional[str] = typer.Option(
        None, "--thread-id", help="LangGraph 线程 id；默认自动生成 case-based id。"
    ),
    only_first_two: bool = typer.Option(
        True,
        "--only-first-two/--full-pipeline",
        help="阶段一仅跑 Skill 1→2（Skill 3-6 未实现）。",
    ),
) -> None:
    """Kick off a fresh writeAgent pipeline."""
    ws = _ensure_workspace(workspace)
    case_id, user_request = _read_request(case, request)
    thread = thread_id or case_id

    init = initial_state(
        case_id=case_id,
        user_request=user_request,
        workspace_root=str(ws),
        state_path=str(ws / "state.json"),
        references_dir=str(references) if references else None,
    )

    export_state_json(ws, dict(init))
    console.print(
        Panel.fit(
            f"[bold green]Run started[/]  case_id={case_id}  thread={thread}\n"
            f"workspace = {ws}",
            title="writeAgent",
        )
    )

    checkpointer = make_checkpointer(ws)
    graph = build_graph(checkpointer=checkpointer, include_optional_skills=not only_first_two)

    final_state = graph.invoke(
        init,
        config={"configurable": {"thread_id": thread}},
    )

    export_state_json(ws, final_state)
    _print_summary(final_state)


# --------------------------------------------------------------------------- #
# resume
# --------------------------------------------------------------------------- #


@app.command()
def resume(
    workspace: Optional[Path] = typer.Option(
        None, "--workspace", "-w", help="工作目录（默认 ./.writeagent）。"
    ),
    thread_id: str = typer.Argument(..., help="之前 run 时返回的线程 id。"),
) -> None:
    """Resume a previously checkpointed thread (e.g. after a crash or user clarification)."""
    ws = _ensure_workspace(workspace)
    checkpointer = make_checkpointer(ws)
    if checkpointer is None:
        raise typer.BadParameter(
            "No checkpointer available; install langgraph-checkpoint-sqlite."
        )
    graph = build_graph(checkpointer=checkpointer)
    final_state = graph.invoke(
        None, config={"configurable": {"thread_id": thread_id}}
    )
    export_state_json(ws, final_state)
    _print_summary(final_state)


# --------------------------------------------------------------------------- #
# inspect
# --------------------------------------------------------------------------- #


@app.command()
def inspect(
    workspace: Optional[Path] = typer.Option(
        None, "--workspace", "-w", help="工作目录（默认 ./.writeagent）。"
    ),
) -> None:
    """Pretty-print the current state.json."""
    ws = _ensure_workspace(workspace)
    state_file = ws / "state.json"
    if not state_file.exists():
        console.print(f"[yellow]No state.json under {ws}[/]")
        raise typer.Exit(code=1)
    data = json.loads(state_file.read_text(encoding="utf-8"))
    syntax = Syntax(
        json.dumps(data, ensure_ascii=False, indent=2),
        "json",
        theme="monokai",
        word_wrap=True,
    )
    console.print(Panel(syntax, title=str(state_file)))


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _print_summary(state: dict) -> None:
    history = state.get("history", [])
    table_lines = [f"stage = {state.get('stage', '?')}", f"history ({len(history)} steps):"]
    for h in history:
        table_lines.append(
            f"  - {h.get('skill', '?'):28} {h.get('status', '?'):6} "
            f"{h.get('duration_ms', 0)}ms  {h.get('message', '')}"
        )
    console.print(Panel("\n".join(table_lines), title="Run summary"))


def main() -> None:  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
