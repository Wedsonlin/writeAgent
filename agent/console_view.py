"""Live, styled console renderer for the LangChain-native ReAct runner.

The runner emits plain ``dict`` events through an optional ``event_sink``
callback. :class:`RichConsoleView` consumes those events synchronously and
prints a beautiful, streaming view of the agent's running process:

- Each Main Agent step: model reasoning, the tool call, and the observation.
- Each delegated SubAgent: a visually nested block with its own steps.

The renderer never raises into the agent run: every dispatch is guarded so a
formatting bug can not abort the orchestration loop.
"""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text


_STATUS_STYLES = {
    "ok": "green",
    "completed": "green",
    "answered": "green",
    "finished": "green",
    "running": "cyan",
    "ask_user": "yellow",
    "needs_input": "yellow",
    "blocked": "yellow",
    "max_steps_exceeded": "yellow",
    "error": "red",
    "failed": "red",
    "fatal": "red",
}

def _status_style(status: str | None) -> str:
    return _STATUS_STYLES.get(str(status or "").lower(), "white")


def _compact(value: Any, *, limit: int = 160) -> str:
    """Render an arbitrary value as a single compact, length-capped line."""
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            text = str(value)
    text = " ".join(text.split())
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text


def _tail(text: Any, *, limit: int = 300) -> str:
    raw = str(text or "")
    raw = raw.strip()
    if len(raw) > limit:
        return "…" + raw[-limit:]
    return raw


def _tool_label(name: str) -> str:
    return name or "?"


def classify_observation_issue(observation: dict[str, Any]) -> str | None:
    """Classify common recoverable tool issues for concise display."""
    text = " ".join(
        str(observation.get(key) or "")
        for key in ("error", "stderr_tail", "message")
    ).lower()
    if not text:
        return None
    if "missing" in text and ("intermediate" in text or "required" in text):
        return "missing prerequisite"
    if "validation failed" in text or "pydantic" in text:
        return "validation warning"
    if "schema" in text or "valid dictionary" in text or "dict_type" in text:
        return "schema mismatch"
    if "path" in text or "file does not exist" in text or "escapes workspace" in text:
        return "path error"
    return None


def compact_workspace_path(path: Any) -> str:
    """Prefer paths relative to the active .writeagent workspace when possible."""
    text = str(path or "")
    normalized = text.replace("\\", "/")
    marker = "/.writeagent/"
    if marker in normalized:
        return normalized.split(marker, 1)[1]
    if normalized.endswith("/.writeagent"):
        return "."
    return text


class RichConsoleView:
    """Stream agent events to the terminal with ``rich`` styling.

    Instances are callables: ``view(event)`` dispatches a single event. The
    same instance handles both Main Agent and nested SubAgent events; SubAgent
    output is indented one level and wrapped in a titled panel.
    """

    def __init__(self, console: Console | None = None, *, indent: str = "    ") -> None:
        self.console = console or Console()
        self._indent = indent

    # -- public sink -------------------------------------------------------- #

    def __call__(self, event: dict[str, Any]) -> None:
        try:
            self._dispatch(event)
        except Exception:  # noqa: BLE001 - rendering must never break the run.
            try:
                self.console.print(
                    f"[dim](console view could not render event: {event.get('type', '?')})[/]"
                )
            except Exception:  # noqa: BLE001
                pass

    # -- dispatch ----------------------------------------------------------- #

    def _dispatch(self, event: dict[str, Any]) -> None:
        kind = str(event.get("type") or "")
        handler = getattr(self, f"_on_{kind}", None)
        if handler is not None:
            handler(event)

    # -- main agent --------------------------------------------------------- #

    def _on_run_start(self, event: dict[str, Any]) -> None:
        body = Text()
        body.append("case_id  ", style="bold")
        body.append(f"{event.get('case_id', '?')}\n")
        body.append("workspace", style="bold")
        body.append(f"  {event.get('workspace', '?')}\n")
        body.append("max_steps", style="bold")
        body.append(f"  {event.get('max_steps', '?')}  ")
        body.append("mode=langchain-react", style="dim")
        self.console.print(Panel(body, title="[bold green]writeAgent · ReAct[/]", border_style="green"))

    def _on_reasoning(self, event: dict[str, Any]) -> None:
        self._print_reasoning(event, prefix="")

    def _on_tool_call(self, event: dict[str, Any]) -> None:
        step = event.get("step")
        name = str(event.get("name") or "?")
        self.console.print(
            Rule(
                f"[bold]Step {step}[/] · [cyan]{_tool_label(name)}[/]",
                style="cyan",
                align="left",
            )
        )
        args = event.get("args") or {}
        if args:
            self.console.print(f"  [cyan]>[/] [dim]{_compact(args, limit=200)}[/]")

    def _on_observation(self, event: dict[str, Any]) -> None:
        name = str(event.get("name") or "")
        observation = event.get("observation") or {}
        self._print_observation(name, observation, prefix="  ")

    def _on_run_end(self, event: dict[str, Any]) -> None:
        status = str(event.get("status") or "?")
        style = _status_style(status)
        body = Text()
        body.append("status  ", style="bold")
        body.append(f"{status}\n", style=style)
        answer = str(event.get("answer") or "").strip()
        if answer:
            body.append("answer  ", style="bold")
            body.append(_tail(answer, limit=320))
        self.console.print(
            Panel(body, title=f"[bold {style}]Run finished[/]", border_style=style)
        )

    # -- subagent ----------------------------------------------------------- #

    def _on_subagent_start(self, event: dict[str, Any]) -> None:
        role = str(event.get("role") or "subagent")
        task = str(event.get("task") or "")
        sub_id = str(event.get("subagent_id") or "")
        body = Text()
        body.append("task        ", style="bold")
        body.append(f"{_compact(task, limit=120)}\n")
        body.append("input_keys  ", style="bold")
        body.append(f"{_compact(event.get('input_keys') or [], limit=120)}\n")
        file_refs = event.get("file_refs") or []
        if file_refs:
            body.append("file_refs   ", style="bold")
            body.append(f"{_compact(file_refs, limit=120)}\n")
        body.append("output_key  ", style="bold")
        body.append(f"{event.get('output_key', '')}")
        self.console.print(
            self._nest(
                Panel(
                    body,
                    title=f"[bold magenta]SubAgent · {role}[/] [dim]{sub_id}[/]",
                    border_style="magenta",
                )
            )
        )

    def _on_subagent_reasoning(self, event: dict[str, Any]) -> None:
        self._print_reasoning(event, prefix=self._indent, sub=True)

    def _on_subagent_tool_call(self, event: dict[str, Any]) -> None:
        step = event.get("step")
        name = str(event.get("name") or "?")
        line = Text(self._indent)
        line.append(f"> sub-step {step} · ", style="magenta")
        line.append(_tool_label(name), style="magenta")
        self.console.print(line)
        args = event.get("args") or {}
        if args:
            self.console.print(f"{self._indent}  [magenta]>[/] [dim]{_compact(args, limit=200)}[/]")

    def _on_subagent_observation(self, event: dict[str, Any]) -> None:
        name = str(event.get("name") or "")
        observation = event.get("observation") or {}
        self._print_observation(name, observation, prefix=self._indent + "  ", accent="magenta")

    def _on_subagent_end(self, event: dict[str, Any]) -> None:
        status = str(event.get("status") or "?")
        style = _status_style(status)
        summary = _compact(event.get("result_summary"), limit=120)
        line = Text(self._indent)
        line.append("< SubAgent ", style="magenta")
        line.append(status, style=style)
        if summary:
            line.append(f" · {summary}", style="dim")
        self.console.print(line)
        errors = event.get("errors") or []
        if errors and status == "failed":
            self.console.print(
                f"{self._indent}  [red]errors[/] [dim]{_compact(errors, limit=200)}[/]"
            )

    # -- shared helpers ----------------------------------------------------- #

    def _print_reasoning(self, event: dict[str, Any], *, prefix: str, sub: bool = False) -> None:
        thought = str(event.get("text") or "").strip()
        reasoning = str(event.get("reasoning_content") or "").strip()
        accent = "magenta" if sub else "blue"
        if reasoning:
            self.console.print(
                f"{prefix}[{accent}]think[/] [dim italic]{_tail(reasoning, limit=500)}[/]"
            )
        if thought:
            self.console.print(
                f"{prefix}[{accent}]reason[/] [italic]{_tail(thought, limit=500)}[/]"
            )

    def _print_observation(
        self,
        name: str,
        observation: dict[str, Any],
        *,
        prefix: str,
        accent: str = "cyan",
    ) -> None:
        if not isinstance(observation, dict):
            self.console.print(f"{prefix}[dim]{_compact(observation, limit=200)}[/]")
            return
        status = observation.get("status")
        style = _status_style(status)
        line = Text(prefix)
        line.append("<- ", style=accent)
        line.append(f"{status or 'ok'}", style=style)
        details = self._observation_details(name, observation)
        if details:
            line.append(f"  {details}", style="dim")
        self.console.print(line)

        issue = classify_observation_issue(observation)
        if issue:
            self.console.print(f"{prefix}  [yellow]issue[/] {issue}")
        stderr = observation.get("stderr_tail")
        if stderr:
            self.console.print(f"{prefix}  [red]stderr[/] [dim]{_tail(stderr, limit=300)}[/]")
        error = observation.get("error")
        if error:
            self.console.print(f"{prefix}  [red]error[/] [dim]{_tail(error, limit=300)}[/]")
        hints = observation.get("contract_hints") or []
        if hints:
            self.console.print(f"{prefix}  [yellow]contract[/] [dim]{_compact(hints, limit=240)}[/]")
        question = observation.get("question")
        if question:
            self.console.print(f"{prefix}  [yellow]question[/] {_compact(question, limit=300)}")
        if observation.get("answer") is not None:
            self.console.print(f"{prefix}  [green]answer[/] {_compact(observation.get('answer'), limit=300)}")

    @staticmethod
    def _observation_details(name: str, observation: dict[str, Any]) -> str:
        parts: list[str] = []
        if name == "run_skill":
            if observation.get("skill"):
                parts.append(f"skill={observation.get('skill')}")
            if observation.get("produced_keys"):
                parts.append(f"produced={_compact(observation.get('produced_keys'), limit=80)}")
            if observation.get("updated_keys"):
                parts.append(f"updated={_compact(observation.get('updated_keys'), limit=80)}")
            if observation.get("duration_ms") is not None:
                parts.append(f"{observation.get('duration_ms')}ms")
        elif name == "delegate_to_subagent":
            if observation.get("output_key"):
                parts.append(f"output_key={observation.get('output_key')}")
            if observation.get("result_summary"):
                parts.append(_compact(observation.get("result_summary"), limit=120))
        elif name == "inspect_state":
            keys = observation.get("state_keys") or []
            if keys:
                parts.append(f"state_keys={_compact(keys, limit=120)}")
        elif name == "ask_user":
            if observation.get("answer") is not None:
                parts.append(f"answer={_compact(observation.get('answer'), limit=100)}")
        elif name == "read_workspace_file":
            if observation.get("path"):
                parts.append(f"path={compact_workspace_path(observation.get('path'))}")
            if observation.get("chars") is not None:
                parts.append(f"chars={observation.get('chars')}")
            if observation.get("truncated"):
                parts.append("truncated=true")
        return "  ".join(parts)

    def _nest(self, renderable: Any) -> Any:
        return Padding(renderable, (0, 0, 0, len(self._indent)))


__all__ = ["RichConsoleView", "classify_observation_issue", "compact_workspace_path"]
