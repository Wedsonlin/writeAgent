"""writeAgent CLI — ``python -m agent`` / ``writeagent`` entry point.

Sub-commands
------------
- ``run``     Kick off workflow or local ReAct mode from a request file/string.
- ``resume``  Continue from the latest workflow checkpoint of an existing thread.
- ``inspect`` Pretty-print the current ``state.json``.
"""

from __future__ import annotations

import json
import uuid
from enum import Enum
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

from .react.skill_registry import SkillRegistry
from .react_runner import ReactRunner
from .skill_runner import SKILLS_DIR, SkillRunner
from .workflow import build_graph, export_state_json, initial_state, make_checkpointer
from .workflow_runner import WorkflowRunner


app = typer.Typer(help="writeAgent — workflow / ReAct 双模式论文写作 Agent CLI")
console = Console()


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORKSPACE = REPO_ROOT / ".writeagent"


class RunMode(str, Enum):
    workflow = "workflow"
    react = "react"


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
    mode: RunMode = typer.Option(
        RunMode.workflow,
        "--mode",
        help="运行模式：workflow=固定 LangGraph 流程；react=本地 ReAct Skill 调度。",
    ),
    max_steps: int = typer.Option(
        24,
        "--max-steps",
        help="react 模式最大决策步数。",
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
    console.print(
        Panel.fit(
            f"[bold green]Run started[/]  mode={mode.value}  case_id={case_id}  thread={thread}\n"
            f"workspace = {ws}",
            title="writeAgent",
        )
    )

    if mode == RunMode.workflow:
        result = WorkflowRunner().run(
            case_id=case_id,
            user_request=user_request,
            workspace_root=ws,
            references_dir=str(references) if references else None,
            thread_id=thread,
            include_optional_skills=not only_first_two,
        )
        _print_summary(result.final_state)
        return

    init = initial_state(
        case_id=case_id,
        user_request=user_request,
        workspace_root=str(ws),
        state_path=str(ws / "state.json"),
        references_dir=str(references) if references else None,
    )
    export_state_json(ws, dict(init))
    registry = SkillRegistry.from_skills_dir(SKILLS_DIR)
    react_result = ReactRunner(
        skill_registry=registry,
        skill_runner=SkillRunner(),
        max_steps=max_steps,
    ).run(
        user_request=user_request,
        workspace_root=ws,
        state_path=ws / "state.json",
    )
    _print_react_summary(react_result)
    if react_result.status == "error":
        raise typer.Exit(code=1)


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


def _print_react_summary(result) -> None:
    lines: list[str] = []
    for step in result.steps:
        observation = step.get("observation", {})
        line = (
            f"[{step.get('step')}] {step.get('action')} "
            f"status={observation.get('status', '?')}"
        )
        if step.get("action") == "run_skill":
            line += (
                f" skill={step.get('action_input', {}).get('skill_name', '?')}"
                f" produced={observation.get('produced_keys', [])}"
                f" updated={observation.get('updated_keys', [])}"
            )
        if observation.get("stderr_tail"):
            line += f" stderr={str(observation.get('stderr_tail'))[:300]}"
        if observation.get("question"):
            line += f" question={observation.get('question')}"
        lines.append(line)
    lines.extend(
        [
            f"Final status: {result.status}",
            f"State path: {result.state_path}",
            f"Trace path: {result.trace_path}",
        ]
    )
    if result.answer:
        lines.append(f"Answer: {result.answer}")
    console.print(Panel("\n".join(lines), title="ReAct run summary"))


def main() -> None:  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
