"""Workspace I/O helpers shared by all Skills.

The workspace layout is::

    <workspace>/
      state.json          # cross-Skill state (single source of truth)
      inputs/             # user-provided files (bibtex, pdf, ...)
      outputs/            # per-Skill rendered artifacts

The orchestrator (LangGraph) and OpenClaw both point a Skill at the workspace via
``--state /path/to/state.json``. The Skill loads, mutates a subtree, then atomically
writes back. Markdown renderings are written next to ``state.json`` under
``outputs/``.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


__all__ = [
    "Workspace",
    "load_state",
    "save_state",
    "append_history",
    "write_output",
    "resolve_workspace",
    "now_iso",
]


def now_iso() -> str:
    """Return the current time as an ISO 8601 string in UTC."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Workspace:
    """A resolved writeAgent workspace.

    Attributes
    ----------
    root :
        The directory containing ``state.json``, ``inputs/`` and ``outputs/``.
    state_path :
        Direct path to the ``state.json`` file.
    """

    root: Path
    state_path: Path

    @property
    def inputs_dir(self) -> Path:
        d = self.root / "inputs"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def outputs_dir(self) -> Path:
        d = self.root / "outputs"
        d.mkdir(parents=True, exist_ok=True)
        return d


def resolve_workspace(state_arg: str | os.PathLike[str] | None) -> Workspace:
    """Determine the workspace directory.

    Priority:
    1. Explicit ``--state`` CLI arg (may point at a file or a directory).
    2. ``WRITEAGENT_WORKSPACE`` environment variable.
    3. ``./.writeagent/`` under the current working directory.

    The chosen directory (and ``state.json`` placeholder) is created on demand.
    """
    candidate: Path
    if state_arg:
        candidate = Path(state_arg).expanduser().resolve()
        if candidate.suffix == ".json":
            root = candidate.parent
            state_path = candidate
        else:
            root = candidate
            state_path = root / "state.json"
    else:
        env_root = os.environ.get("WRITEAGENT_WORKSPACE")
        root = Path(env_root).expanduser().resolve() if env_root else Path.cwd() / ".writeagent"
        state_path = root / "state.json"

    root.mkdir(parents=True, exist_ok=True)
    return Workspace(root=root, state_path=state_path)


def load_state(ws: Workspace) -> dict[str, Any]:
    """Load ``state.json`` or return a fresh skeleton if missing."""
    if not ws.state_path.exists():
        return {
            "case_id": "unnamed-case",
            "user_request": "",
            "stage": "init",
            "history": [],
        }
    try:
        return json.loads(ws.state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(
            f"[_shared.io] WARNING: state.json malformed ({exc}); reinitializing.",
            file=sys.stderr,
        )
        return {
            "case_id": "unnamed-case",
            "user_request": "",
            "stage": "init",
            "history": [],
        }


def save_state(ws: Workspace, state: dict[str, Any]) -> None:
    """Atomically write ``state.json`` to disk.

    We use a temp-file + ``shutil.move`` so that crashes never leave a half-written
    state file (LangGraph's SqliteSaver also reads this file as an audit trail).
    """
    payload = json.dumps(state, ensure_ascii=False, indent=2)
    fd, tmp_name = tempfile.mkstemp(dir=str(ws.root), prefix=".state-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        shutil.move(tmp_name, ws.state_path)
    except Exception:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def append_history(
    state: dict[str, Any],
    skill: str,
    status: str,
    *,
    message: str = "",
    duration_ms: int | None = None,
) -> None:
    """Append a run record to ``state.history``."""
    entry: dict[str, Any] = {
        "skill": skill,
        "ts": now_iso(),
        "status": status,
    }
    if message:
        entry["message"] = message
    if duration_ms is not None:
        entry["duration_ms"] = duration_ms
    state.setdefault("history", []).append(entry)


def write_output(ws: Workspace, name: str, content: str) -> Path:
    """Write a human-readable artifact (Markdown / text) under ``outputs/``."""
    path = ws.outputs_dir / name
    path.write_text(content, encoding="utf-8")
    return path
