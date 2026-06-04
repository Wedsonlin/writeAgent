"""Factory for dynamic Sub-agent specs."""

from __future__ import annotations

from itertools import count
from typing import Any

from ..a2a.types import SubAgentSpec
from .policy import DEFAULT_SUBAGENT_CONSTRAINTS
from .schema_defaults import default_output_schema


class SubAgentFactory:
    """Build a runtime SubAgentSpec from Main Agent action input."""

    def __init__(self, *, parent_agent_id: str = "main") -> None:
        self.parent_agent_id = parent_agent_id
        self._counter = count(1)

    def from_action_input(self, action_input: dict[str, Any]) -> SubAgentSpec:
        subagent_id = str(action_input.get("subagent_id") or f"sa_{next(self._counter):03d}")
        constraints = dict(DEFAULT_SUBAGENT_CONSTRAINTS)
        constraints.update(_dict(action_input.get("constraints")))
        output_key = str(action_input.get("output_key") or "")
        output_schema = action_input.get("output_schema")
        schema_source = "action_input"
        if output_schema is None and output_key:
            output_schema = default_output_schema(output_key)
            if output_schema is not None:
                schema_source = "output_key_default"
        # #region agent log
        _debug_log(
            "H-B",
            "agent/subagents/factory.py:from_action_input",
            "resolved subagent output_schema",
            {
                "output_key": output_key,
                "output_schema": output_schema,
                "schema_source": schema_source,
            },
        )
        # #endregion
        return SubAgentSpec(
            subagent_id=subagent_id,
            parent_agent_id=str(action_input.get("parent_agent_id") or self.parent_agent_id),
            role=str(action_input.get("role") or "dynamic specialist"),
            task=str(action_input.get("task") or ""),
            input_keys=_list_str(action_input.get("input_keys")),
            output_key=output_key,
            skill_context=_list_str(action_input.get("skill_context")),
            prompt_refs=_list_str(action_input.get("prompt_refs")),
            file_refs=_list_str(action_input.get("file_refs")),
            output_schema=output_schema,
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


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict[str, Any]) -> None:
    import json
    import time
    from pathlib import Path

    payload = {
        "sessionId": "755fc4",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    log_path = Path(__file__).resolve().parents[2] / "debug-755fc4.log"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


__all__ = ["SubAgentFactory"]
