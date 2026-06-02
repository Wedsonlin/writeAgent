"""Parsing and serialization helpers for ReAct JSON actions."""

from __future__ import annotations

import json
from typing import Any

from .types import ReactAction


VALID_ACTIONS: set[str] = {"inspect_state", "delegate_to_subagent", "run_skill", "ask_user", "finish"}


def parse_react_action(raw: str) -> ReactAction:
    """Parse a model response into a validated ``ReactAction``."""
    candidate = extract_json_candidate(raw)
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON action: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("ReAct action must be a JSON object.")
    action = payload.get("action")
    if action not in VALID_ACTIONS:
        raise ValueError(f"Unsupported ReAct action: {action!r}")
    action_input = payload.get("action_input") or {}
    if not isinstance(action_input, dict):
        raise ValueError("action_input must be a JSON object.")
    _validate_action_input(action, action_input)
    return ReactAction(
        thought=str(payload.get("thought") or ""),
        action=action,  # type: ignore[arg-type]
        action_input=action_input,
        raw=raw,
    )


def action_to_dict(action: ReactAction) -> dict[str, Any]:
    return {
        "thought": action.thought,
        "action": action.action,
        "action_input": action.action_input,
        "raw": action.raw,
    }


def action_from_dict(payload: dict[str, Any]) -> ReactAction:
    action_name = payload.get("action")
    if action_name not in VALID_ACTIONS:
        raise ValueError(f"Unsupported ReAct action: {action_name!r}")
    action_input = payload.get("action_input") or {}
    if not isinstance(action_input, dict):
        raise ValueError("action_input must be a JSON object.")
    _validate_action_input(action_name, action_input)
    return ReactAction(
        thought=str(payload.get("thought") or ""),
        action=action_name,  # type: ignore[arg-type]
        action_input=action_input,
        raw=str(payload.get("raw") or ""),
    )


def extract_json_candidate(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text


def _validate_action_input(action: str, action_input: dict[str, Any]) -> None:
    if action == "delegate_to_subagent":
        required = ["role", "task", "input_keys", "output_key", "output_schema"]
        missing = [key for key in required if key not in action_input or action_input.get(key) in (None, "", [])]
        if missing:
            raise ValueError(f"delegate_to_subagent missing required fields: {', '.join(missing)}")
        if not isinstance(action_input.get("input_keys"), list):
            raise ValueError("delegate_to_subagent.action_input.input_keys must be a list.")
        if "allowed_tools" in action_input and not isinstance(action_input.get("allowed_tools"), list):
            raise ValueError("delegate_to_subagent.action_input.allowed_tools must be a list.")


__all__ = [
    "VALID_ACTIONS",
    "action_from_dict",
    "action_to_dict",
    "extract_json_candidate",
    "parse_react_action",
]
