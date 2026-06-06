"""Human-in-the-loop policy for Deep Agents."""

from __future__ import annotations


def build_interrupt_on() -> dict[str, object]:
    return {
        "ask_user": {"allowed_decisions": ["respond"]},
        "execute_bash": {"allowed_decisions": ["approve", "edit", "reject"]},
        "update_artifact_manifest": False,
        "update_progress": False,
        "inspect_progress": False,
        "delegate_to_agent": False,
    }
