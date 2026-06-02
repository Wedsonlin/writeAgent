"""SqliteSaver + state.json side-channel.

LangGraph natively persists graph state in ``checkpoints.sqlite`` via
``SqliteSaver``. For OpenClaw compatibility we *also* mirror the latest state
into ``<workspace>/state.json`` after every node so that a parallel OpenClaw
session (or external inspection) sees the same view.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


def make_checkpointer(workspace_root: str | os.PathLike[str]):
    """Return a LangGraph checkpointer rooted at ``<workspace>/checkpoints.sqlite``.

    Falls back to in-memory if ``langgraph-checkpoint-sqlite`` is not installed
    (useful for unit tests that don't need persistence).

    Note: ``SqliteSaver.from_conn_string`` is a context manager in current
    LangGraph versions; we instead construct a sqlite3 connection ourselves
    so the saver's lifetime matches the CLI process.
    """
    root = Path(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    db_path = root / "checkpoints.sqlite"

    try:
        import sqlite3

        from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore[import-not-found]
    except ImportError:
        try:
            from langgraph.checkpoint.memory import MemorySaver  # type: ignore[import-not-found]
        except ImportError:
            return None
        return MemorySaver()

    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    return SqliteSaver(conn)


def export_state_json(workspace_root: str | os.PathLike[str], state: dict[str, Any]) -> Path:
    """Atomically dump the current state dict into ``<workspace>/state.json``.

    Filters out runtime-only keys like ``workspace_root`` / ``state_path`` so
    the on-disk artifact stays clean for downstream consumers.
    """
    runtime_keys = {"workspace_root", "state_path", "references_dir", "retry_count",
                    "next_after_retry", "error"}
    serialisable = {k: v for k, v in state.items() if k not in runtime_keys}

    root = Path(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    target = root / "state.json"

    payload = json.dumps(serialisable, ensure_ascii=False, indent=2)
    fd, tmp = tempfile.mkstemp(dir=str(root), prefix=".state-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        shutil.move(tmp, target)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise
    return target
