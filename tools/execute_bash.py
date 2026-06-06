"""Controlled bash execution tool."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from agent_core.config import REPO_ROOT
from middleware.guardrails import check_command
from project_store.workspace import WorkspaceBoundaryError, resolve_allowed_path
from traces.store import TraceStore


class ExecuteBashInput(BaseModel):
    command: str
    cwd: str | None = None
    timeout_sec: int = Field(default=60, ge=1, le=600)
    purpose: str | None = None


class ExecuteBashResult(BaseModel):
    status: Literal["ok", "failed", "blocked", "timeout"]
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
    allowed_roots: list[str | Path] | None = None,
    trace_store: TraceStore | None = None,
) -> ExecuteBashResult:
    repo = Path(repo_root).resolve()
    roots = [Path(p).resolve() for p in (allowed_roots or [repo])]
    try:
        workdir = resolve_allowed_path(cwd, default=repo, allowed_roots=roots)
    except WorkspaceBoundaryError as exc:
        result = ExecuteBashResult(status="blocked", stderr=str(exc), cwd=str(repo), command=command)
        _trace(trace_store, result, purpose)
        return result

    decision = check_command(command)
    if not decision.allowed:
        result = ExecuteBashResult(status="blocked", stderr=decision.reason, cwd=str(workdir), command=command)
        _trace(trace_store, result, purpose)
        return result

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
        _trace(trace_store, result, purpose)
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
    _trace(trace_store, result, purpose)
    return result


def _snapshot(root: Path) -> set[str]:
    if not root.exists():
        return set()
    return {str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()}


def _trace(trace_store: TraceStore | None, result: ExecuteBashResult, purpose: str | None) -> None:
    if trace_store is not None:
        trace_store.append("execute_bash", status=result.status, payload={**result.model_dump(), "purpose": purpose})
