from __future__ import annotations

from tools.ask_user import ask_user


def test_ask_user_returns_structured_clarification_request():
    result = ask_user(
        "Please provide the topic and paper type.",
        missing_fields=["topic", "paper_type"],
        current_summary="The user wants an academic paper.",
    )

    assert result == {
        "status": "awaiting_user",
        "question": "Please provide the topic and paper type.",
        "missing_fields": ["topic", "paper_type"],
        "current_summary": "The user wants an academic paper.",
    }
