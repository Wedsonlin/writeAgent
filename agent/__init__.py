"""writeAgent · LangGraph orchestrator package.

This package is the *standalone-mode* brain. It is **not** required when Skills
run inside OpenClaw — in that scenario OpenClaw's own ReAct agent dispatches
each Skill based on its ``SKILL.md`` description.

Public entry points
-------------------
- ``agent.cli:app``      Typer CLI exposed as ``python -m agent`` / ``writeagent``.
- ``agent.workflow:build_graph()``  Returns a compiled LangGraph state machine.
- ``agent.workflow:WriteAgentState``  Typed channel definitions + reducers.
- ``agent.workflow_runner:WorkflowRunner``  Fixed pipeline entry wrapper.
"""

__version__ = "0.1.0"
