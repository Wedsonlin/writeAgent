"""Node functions for the writeAgent state graph.

Each Skill node keeps the subprocess boundary around ``SkillRunner.run(...)``.
For Skills that now require Agent-native intermediate data, the workflow layer
runs a fixed Sub-agent preflight before invoking the same ``scripts/run.py``
entrypoint.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from ..a2a.types import SubAgentSpec
from ..clarification import ask_clarification
from ..llm_gateway import LLMGateway
from ..skill_runner import SkillRunner
from ..state_store import MISSING, StateStore, get_path, load_state
from ..subagents.runtime import SubAgentRuntime
from ..trace_store import TraceStore
from .checkpointer import export_state_json
from .state import HistoryEntry, WriteAgentState


_RUNNER = SkillRunner()
MAX_RETRY = 2


# --------------------------------------------------------------------------- #
# Skill node factory
# --------------------------------------------------------------------------- #


def _skill_node(skill_name: str, *, stage_running: str, stage_done: str, node_name: str):
    """Build a LangGraph node that runs a single Skill and merges its output."""

    def node(state: WriteAgentState) -> dict[str, Any]:
        runner_args: list[str] = []
        preflight_error = _ensure_intermediate_for_skill(skill_name, state)
        if preflight_error:
            return {
                "stage": "failed",
                "error": preflight_error,
                "history": [
                    {
                        "skill": skill_name,
                        "ts": _now_iso(),
                        "status": "error",
                        "message": preflight_error[:500],
                    }
                ],
                "next_after_retry": node_name,
            }
        result = _RUNNER.run(skill_name, state["state_path"], extra_args=runner_args)

        history: list[HistoryEntry] = [
            {
                "skill": skill_name,
                "ts": _now_iso(),
                "status": result.status,
                "message": result.stderr.strip()[:500] if result.stderr else "",
                "duration_ms": result.duration_ms,
            }
        ]

        if result.status != "ok":
            # Surface the failure prominently so the user sees the real cause.
            print(
                f"\n[orchestrator] Skill {skill_name} FAILED (exit != 0)\n"
                f"--- STDERR ---\n{result.stderr}\n"
                f"--- STDOUT ---\n{result.stdout}\n",
                file=sys.stderr,
            )
            return {
                "stage": "failed",
                "error": (
                    f"Skill {skill_name} exited with error.\n"
                    f"STDERR:\n{result.stderr}\n"
                    f"STDOUT (tail):\n{result.stdout[-500:]}"
                ),
                "history": history,
                "next_after_retry": node_name,
            }

        # Skill writes the full state dict; we surface its delta to LangGraph.
        delta: dict[str, Any] = {
            "stage": stage_done,
            "history": history,
        }
        produced_keys = [
            "writing_task",
            "literature_report",
            "outline",
            "draft",
            "formatted_draft",
            "polished_draft",
        ]
        for key in produced_keys:
            if key in result.state_after:
                delta[key] = result.state_after[key]

        # Mirror the post-skill state to disk for OpenClaw / external inspection.
        combined = {**state, **delta}
        export_state_json(state["workspace_root"], combined)
        return delta

    node.__name__ = f"{skill_name.replace('-', '_')}_node"
    return node


def _ensure_intermediate_for_skill(skill_name: str, state: WriteAgentState) -> str | None:
    if skill_name not in {"writing-requirement-analysis", "literature-review"}:
        return None
    state_path = Path(state["state_path"])
    workspace_root = Path(state["workspace_root"])
    current = load_state(state_path)
    specs: list[SubAgentSpec] = []
    if skill_name == "writing-requirement-analysis" and get_path(current, "intermediate.requirement.raw_writing_task") is MISSING:
        specs.append(
            SubAgentSpec(
                subagent_id="wf_sa_requirement",
                parent_agent_id="workflow",
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
    if skill_name == "literature-review":
        if get_path(current, "intermediate.literature_review.paper_claims") is MISSING:
            specs.append(
                SubAgentSpec(
                    subagent_id="wf_sa_literature_claims",
                    parent_agent_id="workflow",
                    role="literature analysis specialist",
                    task="Extract key claims and evidence strength from collected reference papers.",
                    input_keys=["writing_task", "references.raw_papers"],
                    output_key="intermediate.literature_review.paper_claims",
                    skill_context=["literature-review"],
                    prompt_refs=["skills/literature-review/prompts/extract_claims.md"],
                    output_schema="PaperClaimsExtraction",
                    allowed_tools=["inspect_state_subset", "read_skill_prompt", "read_skill_context"],
                )
            )
        if get_path(current, "intermediate.literature_review.synthesis") is MISSING:
            specs.append(
                SubAgentSpec(
                    subagent_id="wf_sa_literature_synthesis",
                    parent_agent_id="workflow",
                    role="literature synthesis specialist",
                    task="Synthesize paper claims into clusters, consensus, controversies, and research gaps.",
                    input_keys=["writing_task", "intermediate.literature_review.paper_claims"],
                    output_key="intermediate.literature_review.synthesis",
                    skill_context=["literature-review"],
                    prompt_refs=["skills/literature-review/prompts/synthesize.md"],
                    output_schema="LiteratureSynthesis",
                    allowed_tools=["inspect_state_subset", "read_skill_prompt", "read_skill_context"],
                )
            )
    if not specs:
        return None
    trace_store = TraceStore(workspace_root)
    runtime = SubAgentRuntime(
        llm_gateway=LLMGateway(trace_store=trace_store),
        state_store=StateStore(),
        trace_store=trace_store,
    )
    for spec in specs:
        result = runtime.run(spec, state_path)
        if result.status != "completed":
            return f"Workflow preflight Sub-agent {spec.subagent_id} failed: {result.errors}"
    return None


# --------------------------------------------------------------------------- #
# Concrete Skill nodes
# --------------------------------------------------------------------------- #

skill1_requirement_node = _skill_node(
    "writing-requirement-analysis",
    stage_running="skill1_running",
    stage_done="skill1_done",
    node_name="skill1_requirement",
)

skill2_literature_node = _skill_node(
    "literature-review",
    stage_running="skill2_running",
    stage_done="skill2_done",
    node_name="skill2_literature",
)

skill3_outline_node = _skill_node(
    "paper-outline",
    stage_running="skill3_running",
    stage_done="skill3_done",
    node_name="skill3_outline",
)

skill4_draft_node = _skill_node(
    "paper-content-generation",
    stage_running="skill4_running",
    stage_done="skill4_done",
    node_name="skill4_draft",
)

skill5_format_node = _skill_node(
    "academic-formatting",
    stage_running="skill5_running",
    stage_done="skill5_done",
    node_name="skill5_format",
)

skill6_polish_node = _skill_node(
    "polish-and-plagiarism",
    stage_running="skill6_running",
    stage_done="skill6_done",
    node_name="skill6_polish",
)


# --------------------------------------------------------------------------- #
# human_clarify — loops back to Skill 1 with user-supplied answers
# --------------------------------------------------------------------------- #


def human_clarify_node(state: WriteAgentState) -> dict[str, Any]:
    """Ask the user to fill missing fields, then merge the answers into the request.

    In CLI mode we read from stdin. When deployed behind LangGraph's
    ``interrupt_before`` mechanism this node can also accept an injected
    ``human_response`` channel update without blocking.
    """
    task = state.get("writing_task", {}) or {}
    missing = task.get("missing_info", [])
    if not missing:
        return {"stage": "skill1_done"}

    question = ask_clarification(missing)
    print(question, file=sys.stderr)
    print(
        "\n请在一行内提供补充信息（用 ; 分隔每一项，或留空表示沿用建议默认值）：",
        file=sys.stderr,
    )

    answer = ""
    if sys.stdin.isatty():
        try:
            answer = input("> ").strip()
        except EOFError:
            answer = ""

    addendum = _format_addendum(missing, answer)
    updated_request = state.get("user_request", "") + "\n\n[补充信息]\n" + addendum

    return {
        "user_request": updated_request,
        "stage": "init",
        "history": [
            {
                "skill": "human_clarify",
                "ts": _now_iso(),
                "status": "ok",
                "message": addendum[:200],
            }
        ],
    }


def _format_addendum(missing: list[dict[str, Any]], answer: str) -> str:
    parts = [p.strip() for p in answer.split(";")] if answer else []
    lines: list[str] = []
    for idx, item in enumerate(missing):
        value = parts[idx] if idx < len(parts) and parts[idx] else item.get(
            "suggested_default", "（未提供）"
        )
        lines.append(f"- {item.get('field', f'field_{idx}')}: {value}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# retry_with_fallback
# --------------------------------------------------------------------------- #


def retry_with_fallback_node(state: WriteAgentState) -> dict[str, Any]:
    """Bump the retry counter; the conditional edge decides what comes next."""
    count = int(state.get("retry_count", 0)) + 1
    print(
        f"[orchestrator] retry attempt {count}/{MAX_RETRY} for "
        f"{state.get('next_after_retry', '?')}: {state.get('error', '')[:200]}",
        file=sys.stderr,
    )
    return {
        "retry_count": count,
        "history": [
            {
                "skill": "retry_with_fallback",
                "ts": _now_iso(),
                "status": "ok",
                "message": f"attempt={count}",
            }
        ],
    }


# --------------------------------------------------------------------------- #
# Conditional-edge predicates
# --------------------------------------------------------------------------- #


def after_skill1(state: WriteAgentState) -> str:
    """Decide what follows Skill 1: clarify / proceed / retry."""
    if state.get("stage") == "failed":
        return "retry_with_fallback" if int(state.get("retry_count", 0)) < MAX_RETRY else "__end__"
    task = state.get("writing_task", {}) or {}
    missing = task.get("missing_info", []) or []
    blockers = [m for m in missing if m.get("criticality") == "blocker"]
    if blockers:
        return "human_clarify"
    return "skill2_literature"


def after_skill_generic(next_node: str):
    """Generic post-Skill predicate: success → next; failure → retry/end."""

    def predicate(state: WriteAgentState) -> str:
        if state.get("stage") == "failed":
            if int(state.get("retry_count", 0)) < MAX_RETRY:
                return "retry_with_fallback"
            return "__end__"
        return next_node

    predicate.__name__ = f"after_to_{next_node}"
    return predicate


def after_retry(state: WriteAgentState) -> str:
    """After retry, jump back to whichever node failed."""
    target = state.get("next_after_retry") or "__end__"
    if int(state.get("retry_count", 0)) > MAX_RETRY:
        return "__end__"
    return target


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _now_iso() -> str:
    # local import to avoid circulars when tests stub this module
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")
