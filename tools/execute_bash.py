"""Controlled bash execution tool."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from agent_core.config import REPO_ROOT
from project_store.workspace import resolve_allowed_path


class ExecuteBashInput(BaseModel):
    command: str
    cwd: str | None = None
    timeout_sec: int = Field(default=60, ge=1, le=600)
    purpose: str | None = None


class ExecuteBashResult(BaseModel):
    status: Literal["ok", "failed", "timeout"]
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: int | None = None
    cwd: str
    command: str
    written_files: list[str] = Field(default_factory=list)


def execute_bash(
    command: str,
    cwd: str | None = None,
    timeout_sec: int = 60,
    purpose: str | None = None,
    *,
    repo_root: str | Path = REPO_ROOT,
) -> ExecuteBashResult:
    """Run a shell command and return structured execution details."""
    repo = Path(repo_root).resolve()
    workdir = resolve_allowed_path(cwd, default=repo, allowed_roots=[repo])
    command = _normalize_virtual_command_paths(command)

    before = _snapshot(workdir)
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            command,
            cwd=str(workdir),
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        result = ExecuteBashResult(
            status="timeout",
            exit_code=None,
            stdout=exc.stdout or "",
            stderr=exc.stderr or f"TIMEOUT after {timeout_sec}s",
            duration_ms=duration_ms,
            cwd=str(workdir),
            command=command,
            written_files=sorted(_snapshot(workdir) - before),
        )
        return result

    duration_ms = int((time.perf_counter() - started) * 1000)
    status = "ok" if proc.returncode == 0 else "failed"
    result = ExecuteBashResult(
        status=status,
        exit_code=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        duration_ms=duration_ms,
        cwd=str(workdir),
        command=command,
        written_files=sorted(_snapshot(workdir) - before),
    )
    return result


def _snapshot(root: Path) -> set[str]:
    if not root.exists():
        return set()
    return {str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()}


def _normalize_virtual_command_paths(command: str) -> str:
    replacements = {
        "/skill_packs/": "skill_packs/",
        "/.writeagent/": ".writeagent/",
        "/case/": "case/",
    }
    normalized = command
    for virtual_prefix, local_prefix in replacements.items():
        normalized = normalized.replace(virtual_prefix, local_prefix)
    return normalized
