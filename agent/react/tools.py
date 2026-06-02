"""LangChain tools exposed to the Main Agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..a2a.types import SubAgentResult, SubAgentSpec
from ..skill_runner import SkillRunner
from ..state_store import StateStore, load_state, summarize_state
from ..subagents.factory import SubAgentFactory
from ..subagents.runtime import SubAgentRuntime
from .skill_registry import SkillRegistry


class RunSkillArgs(BaseModel):
    skill_name: str = Field(..., description="Name of the registered Skill to execute.")
    reason: str = Field("", description="Why this Skill is needed now.")


class DelegateToSubagentArgs(BaseModel):
    role: str = Field(..., description="Specialist role for the delegated SubAgent.")
    task: str = Field(..., description="Specific local task to complete.")
    input_keys: list[str] = Field(..., description="State keys the SubAgent may read.")
    output_key: str = Field(..., description="Intermediate state path the SubAgent may write.")
    output_schema: str | dict[str, Any] | None = Field(None, description="Expected output schema name or JSON schema.")
    skill_context: list[str] = Field(default_factory=list, description="Skill docs the SubAgent may use as context.")
    prompt_refs: list[str] = Field(default_factory=list, description="Prompt/template refs the SubAgent may read.")
    allowed_tools: list[str] = Field(default_factory=list, description="Additional explicitly allowed SubAgent tools.")
    success_criteria: list[str] = Field(default_factory=list, description="Criteria for successful completion.")
    constraints: dict[str, Any] = Field(default_factory=dict, description="A2A execution constraints.")
    model_policy: dict[str, Any] = Field(default_factory=dict, description="Optional model policy overrides.")
    write_policy: Literal["return_only", "write_intermediate"] = "write_intermediate"


class AskUserArgs(BaseModel):
    question: str = Field(..., description="Concrete question to ask the user.")
    reason: str = Field("", description="Why this information is required.")


def create_main_tools(
    *,
    skill_registry: SkillRegistry,
    skill_runner: SkillRunner,
    state_path: Path,
    subagent_runtime: SubAgentRuntime | None,
    subagent_factory: SubAgentFactory | None = None,
    tail_chars: int = 3000,
) -> list[Any]:
    """Create LangChain tools with runtime-only values hidden in closures."""
    try:
        from langchain_core.tools import StructuredTool
    except ImportError as exc:  # pragma: no cover - dependency guard.
        raise RuntimeError(
            "langchain-core is required for LangChain-native ReAct mode. "
            "Run `pip install -r requirements-orchestrator.txt`."
        ) from exc

    factory = subagent_factory or SubAgentFactory()

    def inspect_state_tool() -> str:
        return _json(inspect_state(state_path))

    def run_skill_tool(skill_name: str, reason: str = "") -> str:
        return _json(
            run_skill(
                skill_name,
                reason,
                state_path,
                skill_registry=skill_registry,
                skill_runner=skill_runner,
                tail_chars=tail_chars,
            )
        )

    def delegate_to_subagent_tool(**kwargs: Any) -> str:
        if subagent_runtime is None:
            return _json({"tool": "delegate_to_subagent", "status": "fatal", "error": "SubAgentRuntime is not configured."})
        spec = factory.from_action_input(kwargs)
        result = subagent_runtime.run(spec, state_path)
        return _json(subagent_result_to_observation(result))

    def ask_user_tool(question: str, reason: str = "") -> str:
        return _json({"tool": "ask_user", "status": "ask_user", "question": question, "reason": reason})

    return [
        StructuredTool.from_function(
            name="inspect_state",
            description="Read a compact summary of current state.json. This tool does not modify state.",
            func=inspect_state_tool,
        ),
        StructuredTool.from_function(
            name="run_skill",
            description="Execute a registered deterministic Skill script and return a JSON result.",
            func=run_skill_tool,
            args_schema=RunSkillArgs,
        ),
        StructuredTool.from_function(
            name="delegate_to_subagent",
            description="Delegate a local reasoning task to an independent A2A SubAgent graph.",
            func=delegate_to_subagent_tool,
            args_schema=DelegateToSubagentArgs,
        ),
        StructuredTool.from_function(
            name="ask_user",
            description="Ask the user for missing information that blocks progress.",
            func=ask_user_tool,
            args_schema=AskUserArgs,
        ),
    ]


def subagent_result_to_observation(result: SubAgentResult) -> dict[str, Any]:
    return {
        "tool": "delegate_to_subagent",
        "subagent_id": result.subagent_id,
        "parent_agent_id": result.parent_agent_id,
        "status": result.status,
        "output_key": result.output_key,
        "result_summary": result.result_summary,
        "artifacts": result.artifacts,
        "errors": result.errors,
        "needs_followup": result.needs_followup,
        "followup_question": result.followup_question,
        "usage": result.usage,
    }


def run_skill(
    skill_name: str,
    reason: str,
    state_path: Path,
    *,
    skill_registry: SkillRegistry,
    skill_runner: SkillRunner,
    tail_chars: int = 3000,
) -> dict[str, Any]:
    """Invoke one Skill through the shared subprocess runner."""
    state_path = Path(state_path)
    before = load_state(state_path)
    try:
        spec = skill_registry.get(skill_name)
    except KeyError as exc:
        return {
            "tool": "run_skill",
            "skill": skill_name,
            "reason": reason,
            "status": "error",
            "error": str(exc),
            "state_keys": sorted(before.keys()),
            "produced_keys": [],
            "updated_keys": [],
        }

    if not spec.entrypoint_exists:
        return {
            "tool": "run_skill",
            "skill": skill_name,
            "reason": reason,
            "status": "error",
            "error": f"Skill entrypoint is missing: {spec.entrypoint}",
            "state_keys": sorted(before.keys()),
            "produced_keys": [],
            "updated_keys": [],
        }

    try:
        result = skill_runner.run(skill_name, state_path)
    except Exception as exc:  # noqa: BLE001 - surface subprocess/lookup failures to the LLM.
        after = load_state(state_path)
        return {
            "tool": "run_skill",
            "skill": skill_name,
            "reason": reason,
            "status": "error",
            "error": str(exc),
            "duration_ms": 0,
            "stdout_tail": "",
            "stderr_tail": str(exc)[-tail_chars:],
            "state_keys": sorted(after.keys()),
            "produced_keys": _new_keys(before, after),
            "updated_keys": _updated_keys(before, after),
        }

    after = result.state_after or load_state(state_path)
    return {
        "tool": "run_skill",
        "skill": skill_name,
        "reason": reason,
        "status": result.status,
        "duration_ms": result.duration_ms,
        "stdout_tail": _tail(result.stdout, tail_chars),
        "stderr_tail": _tail(result.stderr, tail_chars),
        "state_keys": sorted(after.keys()),
        "produced_keys": _new_keys(before, after),
        "updated_keys": _updated_keys(before, after),
        "state_summary": summarize_state(after),
    }


def inspect_state(state_path: Path) -> dict[str, Any]:
    """Return a compact summary of the current shared state."""
    state_path = Path(state_path)
    state = load_state(state_path)
    return {
        "tool": "inspect_state",
        "status": "ok",
        "state_path": str(state_path),
        "state_keys": sorted(state.keys()),
        "summary": summarize_state(state),
    }


def _json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _tail(text: str, size: int) -> str:
    return text[-size:] if text and len(text) > size else text or ""


def _new_keys(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    return sorted(key for key in after.keys() if key not in before)


def _updated_keys(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    updated = []
    for key, value in after.items():
        if key not in before:
            continue
        if _canonical(before[key]) != _canonical(value):
            updated.append(key)
    return sorted(updated)


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return repr(value)


__all__ = [
    "AskUserArgs",
    "DelegateToSubagentArgs",
    "RunSkillArgs",
    "create_main_tools",
    "inspect_state",
    "run_skill",
    "subagent_result_to_observation",
]
