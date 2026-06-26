"""Local invoke/stream entrypoint for writeAgent."""

from __future__ import annotations

import argparse
from typing import Any, Iterable

from langgraph.types import Command

from .config import RuntimeConfig
from .context import AgentRuntimeContext
from .factory import create_write_agent


class WriteAgentRuntime:
    def __init__(self, config: RuntimeConfig | None = None, agent: Any | None = None) -> None:
        self.config = config or RuntimeConfig()
        self.agent = agent or create_write_agent(self.config)

    def invoke(self, message: str, context: AgentRuntimeContext, *, thread_id: str | None = None) -> Any:
        return self.agent.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config={"configurable": {"thread_id": thread_id or context.project_id}},
            context=context,
            version="v2",
        )

    def stream(self, message: str, context: AgentRuntimeContext, *, thread_id: str | None = None) -> Iterable[Any]:
        return self.agent.stream(
            {"messages": [{"role": "user", "content": message}]},
            config={"configurable": {"thread_id": thread_id or context.project_id}},
            context=context,
            version="v2",
        )

    def resume(self, resume: Any, context: AgentRuntimeContext, *, thread_id: str | None = None) -> Any:
        return self.agent.invoke(
            Command(resume=resume),
            config={"configurable": {"thread_id": thread_id or context.project_id}},
            context=context,
            version="v2",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="writeAgent local Deep Agents CLI")
    parser.add_argument("message")
    parser.add_argument("--project-id", default="default")
    parser.add_argument("--workspace-id", default="local")
    parser.add_argument("--user-id", default="local-user")
    args = parser.parse_args()
    cfg = RuntimeConfig().for_project(args.project_id)
    ctx = AgentRuntimeContext(
        user_id=args.user_id,
        workspace_id=args.workspace_id,
        project_id=cfg.project_id,
        skill_pack_id=cfg.skill_pack_id,
        project_root=str(cfg.project_root),
        artifact_root=str(cfg.artifact_root),
        tmp_root=str(cfg.tmp_root),
        evidence_root=str(cfg.evidence_root),
        cache_root=str(cfg.cache_root),
    )
    result = WriteAgentRuntime(cfg).invoke(args.message, ctx)
    print(result)


if __name__ == "__main__":
    main()
