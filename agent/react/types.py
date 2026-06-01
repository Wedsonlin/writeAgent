"""Typed data structures for the local ReAct runner."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


ReactRunStatus = Literal["finished", "ask_user", "error", "max_steps_exceeded"]
ReactActionName = Literal["run_skill", "inspect_state", "ask_user", "finish"]


@dataclass(frozen=True)
class SkillSpec:
    """A Skill discovered from ``skills/<name>/SKILL.md``."""

    name: str
    path: Path
    description: str
    entrypoint: Path
    raw_markdown: str
    metadata: dict[str, Any] = field(default_factory=dict)
    entrypoint_exists: bool = True


@dataclass
class ReactAction:
    """One JSON action emitted by the ReAct brain."""

    thought: str
    action: ReactActionName
    action_input: dict[str, Any] = field(default_factory=dict)
    raw: str = ""


@dataclass
class ReactRunResult:
    """Final result returned by ``ReactRunner.run``."""

    status: ReactRunStatus
    answer: str
    state_path: Path
    trace_path: Path
    steps: list[dict[str, Any]] = field(default_factory=list)


ReactObservation = dict[str, Any]
