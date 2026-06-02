"""Tool layer exposed to the local ReAct runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..a2a.types import SubAgentResult, SubAgentSpec
from ..skill_runner import SkillRunner
from ..subagents.runtime import SubAgentRuntime
from .skill_registry import SkillRegistry


IMPORTANT_STATE_KEYS = [
    "user_request",
    "stage",
    "history",
    "writing_task",
    "literature_report",
    "outline",
    "draft",
    "formatted_draft",
    "polished_draft",
]


class ReactToolbox:
    """State-aware tool implementations used by ``ReactRunner``."""

    def __init__(
        self,
        *,
        skill_registry: SkillRegistry,
        skill_runner: SkillRunner,
        subagent_runtime: SubAgentRuntime | None = None,
        tail_chars: int = 3000,
    ) -> None:
        self.skill_registry = skill_registry
        self.skill_runner = skill_runner
        self.subagent_runtime = subagent_runtime
        self.tail_chars = tail_chars

    def run_skill(self, skill_name: str, reason: str, state_path: Path) -> dict[str, Any]:
        return run_skill(
            skill_name,
            reason,
            state_path,
            skill_registry=self.skill_registry,
            skill_runner=self.skill_runner,
            tail_chars=self.tail_chars,
        )

    def inspect_state(self, state_path: Path) -> dict[str, Any]:
        return inspect_state(state_path)

    def delegate_to_subagent(self, spec: SubAgentSpec, state_path: Path) -> dict[str, Any]:
        if self.subagent_runtime is None:
            return {"tool": "delegate_to_subagent", "status": "fatal", "error": "SubAgentRuntime is not configured."}
        result = self.subagent_runtime.run(spec, state_path)
        return subagent_result_to_observation(result)

    def finish(self, answer: str, state_path: Path) -> dict[str, Any]:
        return finish(answer, state_path)


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
    before = _read_state(state_path)
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
        after = _read_state(state_path)
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

    after = result.state_after or _read_state(state_path)
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
        "state_summary": _summarize_state(after),
    }


def inspect_state(state_path: Path) -> dict[str, Any]:
    """Return a compact summary of the current shared state."""
    state_path = Path(state_path)
    state = _read_state(state_path)
    if not state:
        return {
            "tool": "inspect_state",
            "status": "ok",
            "state_path": str(state_path),
            "state_keys": [],
            "summary": {},
        }
    return {
        "tool": "inspect_state",
        "status": "ok",
        "state_path": str(state_path),
        "state_keys": sorted(state.keys()),
        "summary": _summarize_state(state),
    }


def finish(answer: str, state_path: Path) -> dict[str, Any]:
    """Return a terminal observation for a completed ReAct run."""
    return {
        "tool": "finish",
        "status": "finished",
        "answer": answer,
        "final_state_path": str(Path(state_path)),
    }


def _read_state(state_path: Path) -> dict[str, Any]:
    try:
        if not state_path.exists():
            return {}
        loaded = json.loads(state_path.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, dict) else {}
    except json.JSONDecodeError as exc:
        return {"_state_error": f"malformed JSON: {exc}"}


def _summarize_state(state: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key in IMPORTANT_STATE_KEYS:
        if key in state:
            summary[key] = _summarize_value(state[key])
    for key in sorted(state.keys()):
        if key not in summary and not key.startswith("_"):
            summary[key] = _summarize_value(state[key])
    return summary


def _summarize_value(value: Any, *, max_text: int = 600, depth: int = 0) -> Any:
    if isinstance(value, str):
        if len(value) <= max_text:
            return value
        return {"type": "str", "length": len(value), "preview": value[:max_text]}
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        items = value[:5]
        return {
            "type": "list",
            "length": len(value),
            "items": [_summarize_value(item, max_text=max_text, depth=depth + 1) for item in items],
        }
    if isinstance(value, dict):
        if depth >= 2:
            return {"type": "dict", "keys": sorted(str(key) for key in value.keys())}
        result: dict[str, Any] = {"type": "dict", "keys": sorted(str(key) for key in value.keys())}
        for key in list(value.keys())[:8]:
            result[str(key)] = _summarize_value(value[key], max_text=max_text, depth=depth + 1)
        return result
    return {"type": type(value).__name__, "repr": repr(value)[:max_text]}


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
