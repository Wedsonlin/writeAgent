"""Local A2A-like protocol for dynamic writeAgent Sub-agents."""

from .types import A2AArtifact, A2AError, SubAgentResult, SubAgentSpec, SubAgentTrace
from .validator import validate_subagent_spec

__all__ = [
    "A2AArtifact",
    "A2AError",
    "SubAgentResult",
    "SubAgentSpec",
    "SubAgentTrace",
    "validate_subagent_spec",
]
