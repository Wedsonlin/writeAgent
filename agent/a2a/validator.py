"""Validation for local A2A delegation requests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..file_tools import validate_workspace_file_ref
from .types import A2AError, SubAgentSpec


ALLOWED_SUBAGENT_TOOLS = {
    "inspect_state",
    "read_state_keys",
    "read_workspace_file",
    "write_intermediate",
    "submit_subagent_result",
}

FORBIDDEN_STATE_KEYS = {
    "writing_task",
    "literature_report",
    "outline",
    "draft",
    "formatted_draft",
    "polished_draft",
}

FORBIDDEN_TOOLS = {
    "run_skill",
    "delegate_to_subagent",
    "finish",
    "ask_user",
    "delete_file",
    "write_final_state",
    "write_outputs_directly",
    "access_unlisted_state_keys",
    "access_unlisted_files",
}


def validate_subagent_spec(
    spec: SubAgentSpec,
    *,
    workspace_root: Path | None = None,
    file_workspace_root: Path | None = None,
) -> list[A2AError]:
    """Return policy/protocol errors for a delegation request."""
    errors: list[A2AError] = []
    _require_text(spec.subagent_id, "subagent_id", errors)
    _require_text(spec.parent_agent_id, "parent_agent_id", errors)
    _require_text(spec.role, "role", errors)
    _require_text(spec.task, "task", errors)
    _require_text(spec.output_key, "output_key", errors)
    if not spec.input_keys:
        errors.append(A2AError("missing_input_keys", "SubAgentSpec.input_keys must not be empty."))
    if spec.write_policy not in {"return_only", "write_intermediate"}:
        errors.append(A2AError("invalid_write_policy", f"Unsupported write_policy: {spec.write_policy}"))

    if spec.write_policy == "write_intermediate" and not spec.output_key.startswith("intermediate."):
        errors.append(
            A2AError(
                "policy_violation",
                "Sub-agent write_policy=write_intermediate requires output_key under state.intermediate.",
                {"output_key": spec.output_key},
            )
        )
    first_key = spec.output_key.split(".", 1)[0]
    if first_key in FORBIDDEN_STATE_KEYS:
        errors.append(
            A2AError(
                "policy_violation",
                "Sub-agent cannot write formal product fields.",
                {"output_key": spec.output_key},
            )
        )

    for tool in spec.allowed_tools:
        if tool in FORBIDDEN_TOOLS or tool not in ALLOWED_SUBAGENT_TOOLS:
            errors.append(
                A2AError(
                    "policy_violation",
                    "Sub-agent tool is not allowed.",
                    {"tool": tool, "allowed_tools": sorted(ALLOWED_SUBAGENT_TOOLS)},
                )
            )

    constraints = dict(spec.constraints or {})
    if constraints.get("can_delegate") is True:
        errors.append(A2AError("policy_violation", "Sub-agents cannot delegate to other agents."))
    if constraints.get("write_scope") not in (None, "intermediate_only"):
        errors.append(
            A2AError(
                "policy_violation",
                "Sub-agent write_scope must be intermediate_only.",
                {"write_scope": constraints.get("write_scope")},
            )
        )
    if constraints.get("allow_file_write") is True:
        errors.append(A2AError("policy_violation", "Sub-agents cannot write files directly."))
    if constraints.get("require_output_schema", True) and spec.output_schema is None:
        errors.append(A2AError("missing_output_schema", "SubAgentSpec.output_schema is required by policy."))

    for prompt_ref in spec.prompt_refs:
        if _unsafe_ref(prompt_ref):
            errors.append(A2AError("policy_violation", "Prompt ref must be a relative in-repository path.", {"prompt_ref": prompt_ref}))
        elif workspace_root and not _is_under((workspace_root / prompt_ref).resolve(), workspace_root.resolve()):
            errors.append(A2AError("policy_violation", "Prompt ref escapes workspace.", {"prompt_ref": prompt_ref}))

    file_root = file_workspace_root or workspace_root
    for file_ref in spec.file_refs:
        if ".." in Path(file_ref).parts:
            errors.append(A2AError("policy_violation", "File ref must not contain parent traversal.", {"file_ref": file_ref}))
            continue
        if file_root is None:
            continue
        file_error = validate_workspace_file_ref(file_ref, workspace_root=file_root)
        if file_error:
            errors.append(A2AError("policy_violation", file_error, {"file_ref": file_ref}))

    return errors


def errors_to_dicts(errors: list[A2AError]) -> list[dict[str, Any]]:
    return [{"code": e.code, "message": e.message, "detail": e.detail} for e in errors]


def _require_text(value: str, field: str, errors: list[A2AError]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(A2AError("missing_field", f"SubAgentSpec.{field} is required."))


def _unsafe_ref(value: str) -> bool:
    path = Path(value)
    return path.is_absolute() or ".." in path.parts


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


__all__ = [
    "ALLOWED_SUBAGENT_TOOLS",
    "FORBIDDEN_STATE_KEYS",
    "FORBIDDEN_TOOLS",
    "errors_to_dicts",
    "validate_subagent_spec",
]
