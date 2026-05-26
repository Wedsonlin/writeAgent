"""writeAgent · LangGraph orchestrator package.

This package is the *standalone-mode* brain. It is **not** required when Skills
run inside OpenClaw — in that scenario OpenClaw's own ReAct agent dispatches
each Skill based on its ``SKILL.md`` description.

Public entry points
-------------------
- ``agent.cli:app``      Typer CLI exposed as ``python -m agent`` / ``writeagent``.
- ``agent.graph:build_graph()``  Returns a compiled LangGraph state machine.
- ``agent.state:WriteAgentState``  Typed channel definitions + reducers.
"""

__version__ = "0.1.0"
