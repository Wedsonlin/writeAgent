"""Tool for requesting missing information from the user."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AskUserInput(BaseModel):
    question: str
    missing_fields: list[str] = Field(default_factory=list)
    current_summary: str | None = None


def ask_user(question: str, missing_fields: list[str] | None = None, current_summary: str | None = None) -> dict:
    """
    Request human clarification through the HITL respond decision.
    
    interrupt data structure:
    {
        "action_requests": [
            {
                "name": "ask_user",
                "args": {
                    "question": "请提供论文主题和类型",
                    "missing_fields": ["topic", "paper_type"],
                    "current_summary": "..."
                }
            }
        ],
        "review_configs": [
            {
                "action_name": "ask_user",
                "allowed_decisions": ["respond"]
            }
        ]
    }

    resume data structure:
    {
        "decisions": [
            {
                "type": "respond",
                "message": "主题是 AI, 类型是综述"
            }
        ]
    }
    """
    return {
        "status": "awaiting_user",
        "question": question,
        "missing_fields": missing_fields or [],
        "current_summary": current_summary,
    }
