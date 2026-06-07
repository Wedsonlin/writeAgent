"""Run-scoped context for the Deep Agents writeAgent runtime."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentRuntimeContext:
    """Immutable runtime context passed to tools and middleware.

    The context carries environment and dependency identifiers only. Business
    artifacts live in files plus ArtifactManifest/ProgressLedger, never here.

    Runtime context is per-run configuration you pass when you invoke the agent.
    It is not automatically included in the model prompt; the model only sees it
    if a tool, middleware,or other logic reads it and adds it to messages or the
    system prompt.
    """

    user_id: str
    workspace_id: str
    project_id: str
    skill_pack_id: str
    artifact_root: str
    locale: str = "zh-CN"
    citation_style: str = "GB/T 7714"
