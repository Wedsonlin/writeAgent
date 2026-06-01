"""Build the LangGraph ``StateGraph`` for the writeAgent pipeline.

Topology
--------

::

    START
      ↓
    skill1_requirement ──(missing_info?)──→ human_clarify ──→ skill1_requirement
      │                                                                 │
      ├── error ──→ retry_with_fallback ──→ skill1_requirement / END    │
      │                                                                 │
      ↓ no missing_info                                                 │
    skill2_literature ←─────────────────────────────────────────────────┘
      │
      ├── error ──→ retry_with_fallback ──→ skill2_literature / END
      ↓
    skill3_outline → skill4_draft → skill5_format → skill6_polish → END
"""

from __future__ import annotations

from typing import Any

from . import nodes
from .state import WriteAgentState


def build_graph(*, checkpointer: Any | None = None, include_optional_skills: bool = True):
    """Return a compiled LangGraph state machine.

    Parameters
    ----------
    checkpointer :
        Any LangGraph checkpointer (``SqliteSaver`` / ``MemorySaver``). ``None``
        gives an uncheckpointed graph (still works, but no resume).
    include_optional_skills :
        Whether to wire Skills 3-6 into the graph. During Phase 1 we set this to
        ``True`` so that the graph topology is honest, but those nodes simply
        fail-fast (no entry script yet) and the edges fall back to ``END``.
    """
    try:
        from langgraph.graph import END, START, StateGraph  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "langgraph is not installed. "
            "Run `pip install -r requirements-orchestrator.txt`."
        ) from exc

    g = StateGraph(WriteAgentState)

    g.add_node("skill1_requirement", nodes.skill1_requirement_node)
    g.add_node("skill2_literature", nodes.skill2_literature_node)
    g.add_node("human_clarify", nodes.human_clarify_node)
    g.add_node("retry_with_fallback", nodes.retry_with_fallback_node)

    if include_optional_skills:
        g.add_node("skill3_outline", nodes.skill3_outline_node)
        g.add_node("skill4_draft", nodes.skill4_draft_node)
        g.add_node("skill5_format", nodes.skill5_format_node)
        g.add_node("skill6_polish", nodes.skill6_polish_node)

    g.add_edge(START, "skill1_requirement")
    g.add_conditional_edges(
        "skill1_requirement",
        nodes.after_skill1,
        {
            "human_clarify": "human_clarify",
            "skill2_literature": "skill2_literature",
            "retry_with_fallback": "retry_with_fallback",
            "__end__": END,
        },
    )
    g.add_edge("human_clarify", "skill1_requirement")

    if include_optional_skills:
        g.add_conditional_edges(
            "skill2_literature",
            nodes.after_skill_generic("skill3_outline"),
            {
                "skill3_outline": "skill3_outline",
                "retry_with_fallback": "retry_with_fallback",
                "__end__": END,
            },
        )
        g.add_conditional_edges(
            "skill3_outline",
            nodes.after_skill_generic("skill4_draft"),
            {
                "skill4_draft": "skill4_draft",
                "retry_with_fallback": "retry_with_fallback",
                "__end__": END,
            },
        )
        g.add_conditional_edges(
            "skill4_draft",
            nodes.after_skill_generic("skill5_format"),
            {
                "skill5_format": "skill5_format",
                "retry_with_fallback": "retry_with_fallback",
                "__end__": END,
            },
        )
        g.add_conditional_edges(
            "skill5_format",
            nodes.after_skill_generic("skill6_polish"),
            {
                "skill6_polish": "skill6_polish",
                "retry_with_fallback": "retry_with_fallback",
                "__end__": END,
            },
        )
        g.add_conditional_edges(
            "skill6_polish",
            nodes.after_skill_generic("__end__"),
            {
                "__end__": END,
                "retry_with_fallback": "retry_with_fallback",
            },
        )
    else:
        g.add_conditional_edges(
            "skill2_literature",
            nodes.after_skill_generic("__end__"),
            {
                "__end__": END,
                "retry_with_fallback": "retry_with_fallback",
            },
        )

    g.add_conditional_edges(
        "retry_with_fallback",
        nodes.after_retry,
        {
            "skill1_requirement": "skill1_requirement",
            "skill2_literature": "skill2_literature",
            **(
                {
                    "skill3_outline": "skill3_outline",
                    "skill4_draft": "skill4_draft",
                    "skill5_format": "skill5_format",
                    "skill6_polish": "skill6_polish",
                }
                if include_optional_skills
                else {}
            ),
            "__end__": END,
        },
    )

    return g.compile(checkpointer=checkpointer) if checkpointer else g.compile()
