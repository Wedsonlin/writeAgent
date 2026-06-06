"""LangGraph checkpointer adapter."""

from __future__ import annotations


def create_checkpointer():
    """Create a local checkpointer for Deep Agents runtime state only."""
    try:
        from langgraph.checkpoint.memory import InMemorySaver
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("langgraph is required for Deep Agents checkpoints") from exc
    return InMemorySaver()
