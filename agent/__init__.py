"""writeAgent local ReAct orchestration package.

This package is the standalone-mode brain. It is not required when Skills run
inside OpenClaw; in that scenario OpenClaw dispatches each Skill from its
``SKILL.md`` description.

Public entry point: ``agent.cli:app`` exposed as ``python -m agent`` /
``writeagent``.
"""

__version__ = "0.1.0"
