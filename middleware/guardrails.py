"""Guardrails for commands and workspace boundaries."""

from __future__ import annotations

import re
from pathlib import Path

from project_store.workspace import is_within_allowed_roots

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


class GuardrailDecision:
    def __init__(self, allowed: bool, reason: str = "", high_risk: bool = False) -> None:
        self.allowed = allowed
        self.reason = reason
        self.high_risk = high_risk


def check_command(command: str) -> GuardrailDecision:
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, flags=re.IGNORECASE):
            return GuardrailDecision(False, f"Command blocked by guardrail pattern: {pattern}")
    high_risk = any(re.search(pattern, command, flags=re.IGNORECASE) for pattern in HIGH_RISK_PATTERNS)
    return GuardrailDecision(True, high_risk=high_risk)


def check_path(path: str | Path, allowed_roots: list[Path]) -> GuardrailDecision:
    if not is_within_allowed_roots(path, allowed_roots):
        return GuardrailDecision(False, f"Path escapes allowed workspace roots: {Path(path).resolve()}")
    return GuardrailDecision(True)


class GuardrailsMiddleware:
    name = "writeagent_guardrails"

    def __init__(self, allowed_roots: list[Path] | None = None) -> None:
        self.allowed_roots = allowed_roots or []
