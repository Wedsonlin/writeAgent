"""Restricted LangChain tools for delegated SubAgents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..a2a.types import SubAgentResult, SubAgentSpec
from ..state_store import StateStore, load_state, summarize_state


DEFAULT_SUBAGENT_TOOLS = {
    "inspect_state",
    "read_state_keys",
    "write_intermediate",
    "submit_subagent_result",
}


class ReadStateKeysArgs(BaseModel):
    keys: list[str] = Field(..., description="Authorized input keys to read.")


class WriteIntermediateArgs(BaseModel):
    value: dict[str, Any] = Field(..., description="JSON object to write to the assigned intermediate output key.")


class SubmitSubAgentResultArgs(BaseModel):
    status: Literal["completed", "failed", "needs_input", "blocked"] = "completed"
    result_summary: str = Field(..., description="Short summary of the SubAgent result.")
    needs_followup: bool = False
    followup_question: str | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)


def create_subagent_tools(
    *,
    spec: SubAgentSpec,
    state_path: Path,
    state_store: StateStore,
    result_sink: dict[str, Any],
) -> list[Any]:
    """Create the restricted tool set for a single SubAgentSpec."""
    try:
        from langchain_core.tools import StructuredTool
    except ImportError as exc:  # pragma: no cover - dependency guard.
        raise RuntimeError(
            "langchain-core is required for LangChain-native ReAct mode. "
            "Run `pip install -r requirements-orchestrator.txt`."
        ) from exc

    def inspect_state_tool() -> str:
        state = load_state(state_path)
        subset = state_store.extract(state_path, spec.input_keys, max_context_chars=int(spec.constraints.get("max_context_chars", 30000)))
        return _json(
            {
                "tool": "inspect_state",
                "status": "ok",
                "allowed_input_keys": spec.input_keys,
                "summary": summarize_state(subset),
                "state_keys": sorted(state.keys()),
            }
        )

    def read_state_keys_tool(keys: list[str]) -> str:
        unauthorized = sorted(set(keys) - set(spec.input_keys))
        if unauthorized:
            return _json({"tool": "read_state_keys", "status": "fatal", "error": "Unauthorized state keys.", "keys": unauthorized})
        return _json({"tool": "read_state_keys", "status": "ok", "values": state_store.extract(state_path, keys)})

    def write_intermediate_tool(value: dict[str, Any]) -> str:
        if spec.write_policy != "write_intermediate":
            return _json({"tool": "write_intermediate", "status": "fatal", "error": "SubAgentSpec.write_policy forbids writes."})
        try:
            state_store.write_intermediate(state_path, spec.output_key, value)
        except Exception as exc:  # noqa: BLE001 - policy failures must be observable.
            return _json({"tool": "write_intermediate", "status": "fatal", "error": str(exc), "output_key": spec.output_key})
        result_sink["wrote_output"] = True
        result_sink["output_key"] = spec.output_key
        return _json(
            {
                "tool": "write_intermediate",
                "status": "ok",
                "output_key": spec.output_key,
                "artifact": {"kind": "state_json_path", "uri": f"state.json#{spec.output_key}"},
            }
        )

    def submit_subagent_result_tool(
        status: str = "completed",
        result_summary: str = "",
        needs_followup: bool = False,
        followup_question: str | None = None,
        errors: list[dict[str, Any]] | None = None,
    ) -> str:
        output_key = spec.output_key if result_sink.get("wrote_output") and status == "completed" else None
        artifacts = [{"kind": "state_json_path", "uri": f"state.json#{spec.output_key}"}] if output_key else []
        result = SubAgentResult(
            subagent_id=spec.subagent_id,
            parent_agent_id=spec.parent_agent_id,
            status=status,  # type: ignore[arg-type]
            output_key=output_key,
            result_summary=result_summary or f"Completed {spec.role}: {spec.task[:120]}",
            artifacts=artifacts,
            errors=list(errors or []),
            needs_followup=needs_followup,
            followup_question=followup_question,
        )
        result_sink["result"] = result
        return _json(
            {
                "tool": "submit_subagent_result",
                "status": "submitted",
                "result": {
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
                },
            }
        )

    return [
        StructuredTool.from_function(
            name="inspect_state",
            description="Inspect only the state subset authorized by SubAgentSpec.input_keys.",
            func=inspect_state_tool,
        ),
        StructuredTool.from_function(
            name="read_state_keys",
            description="Read specific keys from the SubAgentSpec.input_keys allowlist.",
            func=read_state_keys_tool,
            args_schema=ReadStateKeysArgs,
        ),
        StructuredTool.from_function(
            name="write_intermediate",
            description="Write a JSON object to the SubAgentSpec.output_key intermediate path.",
            func=write_intermediate_tool,
            args_schema=WriteIntermediateArgs,
        ),
        StructuredTool.from_function(
            name="submit_subagent_result",
            description="Submit the final A2A SubAgentResult and stop the SubAgent graph.",
            func=submit_subagent_result_tool,
            args_schema=SubmitSubAgentResultArgs,
        ),
    ]


def _json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


__all__ = [
    "DEFAULT_SUBAGENT_TOOLS",
    "ReadStateKeysArgs",
    "SubmitSubAgentResultArgs",
    "WriteIntermediateArgs",
    "create_subagent_tools",
]
