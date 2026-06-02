"""Build the LangGraph ``StateGraph`` for local ReAct scheduling."""

from __future__ import annotations

from .nodes import ReactNodes, route_after_decide, route_after_execute
from .state import ReactGraphState


def build_graph(nodes: ReactNodes):
    """Build the LangGraph state machine for local ReAct scheduling."""
    try:
        from langgraph.graph import END, START, StateGraph  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "langgraph is required for react mode. "
            "Run `pip install -r requirements-orchestrator.txt`."
        ) from exc

    graph = StateGraph(ReactGraphState)
    graph.add_node("decide_action", nodes.decide_action_node)
    graph.add_node("execute_action", nodes.execute_action_node)
    graph.add_edge(START, "decide_action")
    graph.add_conditional_edges(
        "decide_action",
        route_after_decide,
        {
            "execute_action": "execute_action",
            "__end__": END,
        },
    )
    graph.add_conditional_edges(
        "execute_action",
        route_after_execute,
        {
            "decide_action": "decide_action",
            "__end__": END,
        },
    )
    return graph.compile()


__all__ = ["build_graph"]
