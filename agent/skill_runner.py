"""Invoke a Skill exactly the same way OpenClaw would: as a subprocess.

Why subprocess instead of in-process import?
    * **Parity with OpenClaw.** OpenClaw runs ``python {baseDir}/scripts/run.py``
      via bash; using subprocess in standalone mode guarantees we exercise the
      same boundary (stdin/stdout/stderr, exit codes, env vars).
    * **Isolation.** A Skill crash never poisons the LangGraph process.
    * **Trivially swappable.** A future Skill written in Node.js / Rust just
      changes the entry command — the runner doesn't care.

The runner reads ``state.json`` *after* the Skill exits and returns the delta to
LangGraph as a partial state update.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"


@dataclass
class SkillResult:
    skill: str
    status: str          # "ok" | "error"
    duration_ms: int
    stdout: str
    stderr: str
    state_after: dict[str, Any]


class SkillRunner:
    """Thin wrapper that invokes ``skills/<name>/scripts/run.py``."""

    def __init__(
        self,
        *,
        python_executable: str | None = None,
        timeout: float = 600.0,
    ) -> None:
        self.python = python_executable or sys.executable # Python interpreter, default using current's
        self.timeout = timeout # timeout for skill subprocess

    def run(
        self,
        skill_name: str,
        state_path: str | os.PathLike[str],
        *,
        extra_args: list[str] | None = None,
        env_overrides: dict[str, str] | None = None,
    ) -> SkillResult:
        """
        Run a Skill end-to-end and return its result + the post-run state.
        1. Locate `skills/<skill_name>/scripts/run.py` according to `skill_name`.
        2. Check whether `run.py` exists.
        3. Construct the command: python run.py --state state.json
        4. Set the working directory to the current Skill directory.
        5. Set `PYTHONPATH` so that the Skill can import shared modules under `skills/_shared`.
        6. Start a subprocess to execute the Skill.
        7. Capture `stdout`, `stderr`, and the return code.
        8. Determine whether the execution succeeded or failed based on `returncode`.
        9. If the execution succeeds, read the updated state file.
        10. Encapsulate the execution result into a `SkillResult` and return it.
        11. If a timeout occurs, return an `error` status.
        """
        skill_dir = SKILLS_DIR / skill_name
        entry = skill_dir / "scripts" / "run.py"
        if not entry.exists():
            raise FileNotFoundError(
                f"Skill entry not found: {entry}. "
                f"Make sure skills/{skill_name}/scripts/run.py exists."
            )

        cmd: list[str] = [ # python skills/<skill_name>/scripts/run.py --state case/state.json
            self.python,
            str(entry),
            "--state",
            str(state_path),
        ]
        if extra_args:
            cmd.extend(extra_args)

        env = os.environ.copy()
        # Allow Skills to import shared modules via `from _shared.llm import ...`
        existing_path = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = ( # PYTHONPATH=skills:/some/old/path
            str(SKILLS_DIR) + (os.pathsep + existing_path if existing_path else "")
        )
        if env_overrides:
            env.update(env_overrides)

        started = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(skill_dir),
                env=env,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding="utf-8",
                errors="replace",
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            status = "ok" if proc.returncode == 0 else "error"
            state_after = self._read_state(state_path) if status == "ok" else {}
            return SkillResult(
                skill=skill_name,
                status=status,
                duration_ms=duration_ms,
                stdout=proc.stdout,
                stderr=proc.stderr,
                state_after=state_after,
            )
        except subprocess.TimeoutExpired as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return SkillResult(
                skill=skill_name,
                status="error",
                duration_ms=duration_ms,
                stdout=exc.stdout or "",
                stderr=f"TIMEOUT after {self.timeout}s",
                state_after={},
            )

    @staticmethod
    def _read_state(state_path: str | os.PathLike[str]) -> dict[str, Any]:
        path = Path(state_path)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
