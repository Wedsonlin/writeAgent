"""Tool for requesting missing information from the user."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AskUserInput(BaseModel):
    question: str
    missing_fields: list[str] = Field(default_factory=list)
    current_summary: str | None = None


def ask_user(question: str, missing_fields: list[str] | None = None, current_summary: str | None = None) -> dict:
    """Request human clarification through the HITL respond decision."""
    return {
        "status": "awaiting_user",
        "question": question,
        "missing_fields": missing_fields or [],
        "current_summary": current_summary,
    }
