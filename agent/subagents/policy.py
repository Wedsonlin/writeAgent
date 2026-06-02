"""Safety policy for dynamically derived Sub-agents."""

from __future__ import annotations

from pathlib import Path

from ..a2a.validator import ALLOWED_SUBAGENT_TOOLS, FORBIDDEN_TOOLS
from ..a2a.types import A2AError, SubAgentSpec


DEFAULT_SUBAGENT_CONSTRAINTS = {
    "max_steps": 3,
    "max_context_chars": 30000,
    "max_output_chars": 50000,
    "can_delegate": False,
    "write_scope": "intermediate_only",
    "require_output_schema": True,
    "allow_file_write": False,
}


def merged_constraints(spec: SubAgentSpec) -> dict[str, object]:
    merged = dict(DEFAULT_SUBAGENT_CONSTRAINTS)
    merged.update(spec.constraints or {})
    return merged


def is_allowed_tool(spec: SubAgentSpec, tool_name: str) -> bool:
    return tool_name in spec.allowed_tools and tool_name in ALLOWED_SUBAGENT_TOOLS and tool_name not in FORBIDDEN_TOOLS


def assert_allowed_tool(spec: SubAgentSpec, tool_name: str) -> None:
    if not is_allowed_tool(spec, tool_name):
        raise PermissionError(f"Sub-agent tool is not allowed: {tool_name}")


def assert_prompt_ref_allowed(spec: SubAgentSpec, prompt_ref: str, repo_root: Path) -> Path:
    if prompt_ref not in spec.prompt_refs:
        raise PermissionError(f"Prompt ref is not authorized: {prompt_ref}")
    path = (repo_root / prompt_ref).resolve()
    try:
        path.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise PermissionError(f"Prompt ref escapes repository: {prompt_ref}") from exc
    return path


def policy_error(code: str, message: str, **detail: object) -> A2AError:
    return A2AError(code=code, message=message, detail=dict(detail))


__all__ = [
    "DEFAULT_SUBAGENT_CONSTRAINTS",
    "assert_allowed_tool",
    "assert_prompt_ref_allowed",
    "is_allowed_tool",
    "merged_constraints",
    "policy_error",
]
