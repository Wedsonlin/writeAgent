"""writeAgent CLI — ``python -m agent`` / ``writeagent`` entry point.

Sub-commands
------------
- ``run``     Kick off the local LangChain ReAct runner from a request file/string.
- ``inspect`` Pretty-print the current ``state.json``.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Optional


def _configure_utf8_stdout() -> None:
    """Best-effort switch console streams to UTF-8 so rich glyphs never crash.

    On Chinese Windows the default code page is GBK, which raises
    ``UnicodeEncodeError`` on box-drawing / arrow glyphs. ``errors='replace'``
    keeps output flowing on terminals that still can not render a character.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001 - leave stream as-is if unsupported.
                pass


_configure_utf8_stdout()

try:
    import typer
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "typer is not installed. Run `pip install -r requirements-orchestrator.txt`."
    ) from exc

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from .console_view import RichConsoleView
from .human_input import ConsoleHumanInput
from .react.skill_contract_inference import build_contract_inference_prompt, generated_contract_path
from .react.skill_registry import SkillRegistry
from .react_runner import ReactRunner
from .skill_runner import SKILLS_DIR, SkillRunner
from .state_store import write_state


app = typer.Typer(help="writeAgent — 本地 LangChain ReAct 论文写作 Agent CLI")
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
    max_steps: int = typer.Option(
        24,
        "--max-steps",
        help="最大 ReAct 决策步数。",
    ),
    stream: bool = typer.Option(
        True,
        "--stream/--no-stream",
        help="实时流式展示每一步 ReAct 推理 / 工具调用 / SubAgent 委派（默认开启）。",
    ),
    human_in_loop: bool = typer.Option(
        True,
        "--human-in-loop/--no-human-in-loop",
        help="遇到 ask_user 时在当前终端收集用户补充信息并继续执行（默认开启）。",
    ),
) -> None:
    """Kick off a fresh writeAgent pipeline."""
    ws = _ensure_workspace(workspace)
    case_id, user_request = _read_request(case, request)

    view = RichConsoleView(console) if stream else None
    human_input_provider = ConsoleHumanInput(console) if human_in_loop else None
    if view is not None:
        view({"type": "run_start", "case_id": case_id, "workspace": str(ws), "max_steps": max_steps})
    else:
        console.print(
            Panel.fit(
                f"[bold green]Run started[/]  mode=langchain-react  case_id={case_id}\n"
                f"workspace = {ws}",
                title="writeAgent",
            )
        )

    init = _initial_state(
        case_id=case_id,
        user_request=user_request,
        workspace_root=str(ws),
        state_path=str(ws / "state.json"),
        references_dir=str(references) if references else None,
    )
    write_state(ws / "state.json", init)
    registry = SkillRegistry.from_skills_dir(SKILLS_DIR)
    react_result = ReactRunner(
        skill_registry=registry,
        skill_runner=SkillRunner(),
        max_steps=max_steps,
        event_sink=view,
        human_input_provider=human_input_provider,
    ).run(
        user_request=user_request,
        workspace_root=ws,
        state_path=ws / "state.json",
    )
    if view is not None:
        view({"type": "run_end", "status": react_result.status, "answer": react_result.answer})
        _print_react_outcome(react_result)
    else:
        _print_react_summary(react_result)
    if react_result.status == "error":
        raise typer.Exit(code=1)


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
# infer-contract
# --------------------------------------------------------------------------- #


@app.command("infer-contract")
def infer_contract(
    skill: str = typer.Argument(..., help="Skill name under ./skills/."),
) -> None:
    """Print an LLM-ready prompt for generating a cached Skill contract."""
    skill_dir = SKILLS_DIR / skill
    if not skill_dir.exists():
        console.print(f"[red]Unknown skill directory: {skill_dir}[/]")
        raise typer.Exit(code=1)
    prompt = build_contract_inference_prompt(skill_dir, schemas_dir=REPO_ROOT / "schemas")
    console.print(
        Panel(
            f"Review or send this prompt to an LLM, then save valid JSON to:\n"
            f"{generated_contract_path(skill_dir)}",
            title="Skill contract inference scaffold",
        )
    )
    console.print(Syntax(prompt, "json", theme="monokai", word_wrap=True))


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _initial_state(
    *,
    case_id: str,
    user_request: str,
    workspace_root: str,
    state_path: str,
    references_dir: str | None = None,
) -> dict:
    state = {
        "case_id": case_id,
        "user_request": user_request,
        "stage": "init",
        "history": [],
        "workspace_root": workspace_root,
        "state_path": state_path,
    }
    if references_dir:
        state["references_dir"] = references_dir
    return state


def _print_react_outcome(result) -> None:
    """Concise final panel for stream mode (per-step detail already shown live)."""
    lines = [
        f"State path: {result.state_path}",
        f"Trace path: {result.trace_path}",
    ]
    console.print(Panel("\n".join(lines), title="Artifacts", border_style="dim"))


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
