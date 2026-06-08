"""Guardrails for commands and workspace boundaries."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Awaitable, Callable

from langchain.agents.middleware import AgentMiddleware
from langchain.messages import ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langgraph.types import Command

from project_store.workspace import WorkspaceBoundaryError, is_within_allowed_roots, resolve_allowed_path

DANGEROUS_PATTERNS = [
    r"\bsudo\b",
    r"\brm\s+-rf\b",
    r"\bcurl\b",
    r"\bwget\b",
    r"\bssh\b",
    r"\bscp\b",
    r"\bchmod\s+777\b",
    r"\bformat\b",
    r"\bdel\s+/s\b",
    r"\bRemove-Item\b.*\b-Recurse\b.*\b-Force\b",
]

HIGH_RISK_PATTERNS = [r"\bgit\s+push\b", r"\bpip\s+install\b", r"\bnpm\s+install\b"]

_ARG_PATTERN = r"""(?:[^\s;&|`$<>]+|"[^"&|`$<>]*"|'[^'&|`$<>]*')"""
ALLOWED_COMMAND_PATTERNS = [
    re.compile(
        rf"""^\s*(?:python|python3|py)(?:\.exe)?\s+["']?[\\/]?skill_packs[\\/][^"'\s]+[\\/]skills[\\/][^"'\s\\/]+[\\/]scripts[\\/]run\.py["']?(?:\s+{_ARG_PATTERN})*\s*$""",
        flags=re.IGNORECASE,
    )
]


class GuardrailDecision:
    def __init__(self, allowed: bool, reason: str = "", high_risk: bool = False) -> None:
        self.allowed = allowed
        self.reason = reason
        self.high_risk = high_risk


def check_command(command: str) -> GuardrailDecision:
    if not any(pattern.search(command) for pattern in ALLOWED_COMMAND_PATTERNS):
        return GuardrailDecision(False, "Command is not in the execute_bash whitelist.")
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, flags=re.IGNORECASE):
            return GuardrailDecision(False, f"Command blocked by guardrail pattern: {pattern}")
    high_risk = any(re.search(pattern, command, flags=re.IGNORECASE) for pattern in HIGH_RISK_PATTERNS)
    return GuardrailDecision(True, high_risk=high_risk)


def check_path(path: str | Path, allowed_roots: list[Path]) -> GuardrailDecision:
    if not is_within_allowed_roots(path, allowed_roots):
        return GuardrailDecision(False, f"Path escapes allowed workspace roots: {Path(path).resolve()}")
    return GuardrailDecision(True)


class GuardrailsMiddleware(AgentMiddleware):
    name = "writeagent_guardrails"

    def __init__(self, allowed_roots: list[Path] | None = None, *, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.allowed_roots = allowed_roots or []

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        if request.tool_call["name"] != "execute_bash":
            return handler(request)

        args = request.tool_call["args"]
        command = str(args.get("command", ""))
        cwd = args.get("cwd")
        decision = self._check_execute_bash(command, cwd)
        if decision.allowed:
            return handler(request)

        payload = {
            "status": "blocked",
            "reason": decision.reason,
            "command": command,
            "cwd": cwd,
        }
        return ToolMessage(
            content=json.dumps(payload, ensure_ascii=False),
            tool_call_id=request.tool_call["id"],
        )

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        if request.tool_call["name"] != "execute_bash":
            return await handler(request)

        args = request.tool_call["args"]
        command = str(args.get("command", ""))
        cwd = args.get("cwd")
        decision = self._check_execute_bash(command, cwd)
        if decision.allowed:
            return await handler(request)

        payload = {
            "status": "blocked",
            "reason": decision.reason,
            "command": command,
            "cwd": cwd,
        }
        return ToolMessage(
            content=json.dumps(payload, ensure_ascii=False),
            tool_call_id=request.tool_call["id"],
        )

    def _check_execute_bash(self, command: str, cwd: str | None) -> GuardrailDecision:
        try:
            resolve_allowed_path(cwd, default=self.repo_root, allowed_roots=self.allowed_roots)
        except WorkspaceBoundaryError as exc:
            return GuardrailDecision(False, str(exc))
        return check_command(command)
