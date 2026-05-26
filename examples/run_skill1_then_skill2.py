"""End-to-end runner for Skill 1 → Skill 2 in standalone mode (no LangGraph required).

Use this for quick offline validation. It bypasses the LangGraph orchestrator
and invokes the same subprocess pathway OpenClaw would.

Example::

    set WRITEAGENT_MOCK_LLM=1
    python examples/run_skill1_then_skill2.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
WORKSPACE = REPO / ".writeagent"
STATE = WORKSPACE / "state.json"
CASE_REQUEST = REPO / "case" / "00-用户原始需求.md"
SEED_BIB = REPO / "case" / "references" / "seed.bib"


def bootstrap_state() -> None:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    user_request = CASE_REQUEST.read_text(encoding="utf-8")
    state = {
        "case_id": "writing-agent-design-2026",
        "user_request": user_request,
        "stage": "init",
        "history": [],
    }
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[bootstrap] wrote {STATE}")


def run_skill(skill_dir: Path, args: list[str]) -> int:
    cmd = [sys.executable, str(skill_dir / "scripts" / "run.py"), "--state", str(STATE)] + args
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    # Make `_shared` importable inside the skill subprocess.
    env["PYTHONPATH"] = str(REPO / "skills") + os.pathsep + env.get("PYTHONPATH", "")
    print(f"\n[runner] $ {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(skill_dir), env=env, encoding="utf-8")
    return proc.returncode


def main() -> int:
    bootstrap_state()
    rc1 = run_skill(
        REPO / "skills" / "writing-requirement-analysis",
        extra_args := [],
    )
    if rc1 != 0:
        print(f"[runner] Skill 1 failed with code {rc1}", file=sys.stderr)
        return rc1

    rc2 = run_skill(
        REPO / "skills" / "literature-review",
        ["--refs", str(SEED_BIB), "--citation-style", "GB/T 7714"],
    )
    if rc2 != 0:
        print(f"[runner] Skill 2 failed with code {rc2}", file=sys.stderr)
        return rc2

    print("\n[runner] Pipeline completed. See .writeagent/outputs/ for artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
