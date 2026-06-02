"""End-to-end runner for Skill 1 → Skill 2 in standalone mode (no LangGraph required).

Use this for quick offline validation. It bypasses LangGraph but still follows
the Agent-native boundary: SubAgentRuntime writes ``state.intermediate`` first,
then Skill subprocesses validate, render, and persist formal outputs.

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
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from agent.a2a.types import SubAgentSpec
from agent.llm_gateway import LLMGateway
from agent.state_store import StateStore
from agent.subagents.runtime import SubAgentRuntime
from agent.trace_store import TraceStore


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


def delegate(spec: SubAgentSpec) -> None:
    trace_store = TraceStore(WORKSPACE)
    runtime = SubAgentRuntime(
        llm_gateway=LLMGateway(trace_store=trace_store),
        state_store=StateStore(),
        trace_store=trace_store,
    )
    result = runtime.run(spec, STATE)
    if result.status != "completed":
        raise RuntimeError(f"Sub-agent failed: {result.errors}")


def main() -> int:
    bootstrap_state()
    delegate(
        SubAgentSpec(
            subagent_id="example_requirement",
            parent_agent_id="example",
            role="requirement analysis specialist",
            task="Convert the user request into a structured writing task draft.",
            input_keys=["user_request"],
            output_key="intermediate.requirement.raw_writing_task",
            skill_context=["writing-requirement-analysis"],
            prompt_refs=["skills/writing-requirement-analysis/prompts/extract_writing_task.md"],
            output_schema="WritingTask",
            allowed_tools=["inspect_state_subset", "read_skill_prompt", "read_skill_context"],
        )
    )
    rc1 = run_skill(
        REPO / "skills" / "writing-requirement-analysis",
        [],
    )
    if rc1 != 0:
        print(f"[runner] Skill 1 failed with code {rc1}", file=sys.stderr)
        return rc1

    delegate(
        SubAgentSpec(
            subagent_id="example_literature_claims",
            parent_agent_id="example",
            role="literature analysis specialist",
            task="Extract key claims and evidence strength from collected references.",
            input_keys=["writing_task", "references.raw_papers"],
            output_key="intermediate.literature_review.paper_claims",
            skill_context=["literature-review"],
            prompt_refs=["skills/literature-review/prompts/extract_claims.md"],
            output_schema="PaperClaimsExtraction",
            allowed_tools=["inspect_state_subset", "read_skill_prompt", "read_skill_context"],
        )
    )
    delegate(
        SubAgentSpec(
            subagent_id="example_literature_synthesis",
            parent_agent_id="example",
            role="literature synthesis specialist",
            task="Synthesize paper claims into clusters, consensus, controversies, and gaps.",
            input_keys=["writing_task", "intermediate.literature_review.paper_claims"],
            output_key="intermediate.literature_review.synthesis",
            skill_context=["literature-review"],
            prompt_refs=["skills/literature-review/prompts/synthesize.md"],
            output_schema="LiteratureSynthesis",
            allowed_tools=["inspect_state_subset", "read_skill_prompt", "read_skill_context"],
        )
    )
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
