"""Factory for dynamic Sub-agent specs."""

from __future__ import annotations

from itertools import count
from typing import Any

from ..a2a.types import SubAgentSpec
from .policy import DEFAULT_SUBAGENT_CONSTRAINTS


class SubAgentFactory:
    """Build a runtime SubAgentSpec from Main Agent action input."""

    def __init__(self, *, parent_agent_id: str = "main") -> None:
        self.parent_agent_id = parent_agent_id
        self._counter = count(1)

    def from_action_input(self, action_input: dict[str, Any]) -> SubAgentSpec:
        subagent_id = str(action_input.get("subagent_id") or f"sa_{next(self._counter):03d}")
        constraints = dict(DEFAULT_SUBAGENT_CONSTRAINTS)
        constraints.update(_dict(action_input.get("constraints")))
        return SubAgentSpec(
            subagent_id=subagent_id,
            parent_agent_id=str(action_input.get("parent_agent_id") or self.parent_agent_id),
            role=str(action_input.get("role") or "dynamic specialist"),
            task=str(action_input.get("task") or ""),
            input_keys=_list_str(action_input.get("input_keys")),
            output_key=str(action_input.get("output_key") or ""),
            skill_context=_list_str(action_input.get("skill_context")),
            prompt_refs=_list_str(action_input.get("prompt_refs")),
            output_schema=action_input.get("output_schema"),
            allowed_tools=_list_str(action_input.get("allowed_tools")),
            success_criteria=_list_str(action_input.get("success_criteria")),
            constraints=constraints,
            model_policy=_dict(action_input.get("model_policy")),
            write_policy=action_input.get("write_policy") or "write_intermediate",
        )


def _list_str(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


__all__ = ["SubAgentFactory"]
