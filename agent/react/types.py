"""Typed data structures for the LangChain-native ReAct runner."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from .skill_contracts import SkillContract


ReactRunStatus = Literal["finished", "ask_user", "error", "max_steps_exceeded"]


@dataclass(frozen=True)
class SkillSpec:
    """A Skill discovered from ``skills/<name>/SKILL.md``."""

    name: str
    path: Path
    description: str
    entrypoint: Path
    raw_markdown: str
    metadata: dict[str, Any] = field(default_factory=dict)
    contract: SkillContract = field(default_factory=SkillContract)
    entrypoint_exists: bool = True


@dataclass
class ReactRunResult:
    """Final result returned by ``ReactRunner.run``."""

    status: ReactRunStatus
    answer: str
    state_path: Path
    trace_path: Path
    steps: list[dict[str, Any]] = field(default_factory=list)


ReactObservation = dict[str, Any]


ToolCallRecord = dict[str, Any]
