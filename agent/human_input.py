"""Human-in-the-loop input providers for interactive agent runs."""

from __future__ import annotations

from typing import Protocol

from rich.console import Console
from rich.panel import Panel


class HumanInputProvider(Protocol):
    """Callable interface used by tools that need a user's free-form answer."""

    def __call__(self, question: str, reason: str = "") -> str:
        """Ask a question and return the user's answer."""


class ConsoleHumanInput:
    """Prompt for a free-form user answer in the current terminal session."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def __call__(self, question: str, reason: str = "") -> str:
        body = question.strip()
        if reason.strip():
            body = f"{body}\n\n[dim]Reason: {reason.strip()}[/]"
        self.console.print(Panel(body, title="[bold yellow]Human input requested[/]", border_style="yellow"))
        return self.console.input("[bold yellow]Your answer> [/]")


__all__ = ["ConsoleHumanInput", "HumanInputProvider"]
