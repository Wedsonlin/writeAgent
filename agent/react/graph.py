"""Build the LangGraph graph for LangChain-native Main Agent ReAct."""

from __future__ import annotations

from .nodes import ReactNodes
from .routers import route_after_main_agent, route_after_main_tools
from .state import MainAgentState


def build_graph(nodes: ReactNodes):
    """Build the Main Agent tool-calling state machine."""
    try:
        from langgraph.graph import END, START, StateGraph  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "langgraph is required for react mode. "
            "Run `pip install -r requirements-orchestrator.txt`."
        ) from exc

    graph = StateGraph(MainAgentState)
    graph.add_node("main_agent", nodes.main_agent_node)
    graph.add_node("main_tools", nodes.main_tools_node)
    graph.add_edge(START, "main_agent")
    graph.add_conditional_edges(
        "main_agent",
        route_after_main_agent,
        {
            "main_tools": "main_tools",
            "__end__": END,
        },
    )
    graph.add_conditional_edges(
        "main_tools",
        route_after_main_tools,
        {
            "main_agent": "main_agent",
            "__end__": END,
        },
    )
    return graph.compile()


__all__ = ["build_graph"]
