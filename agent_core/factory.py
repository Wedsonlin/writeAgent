"""Deep Agents factory for writeAgent."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
from langchain_core.tools import StructuredTool

from delegation.registry import AgentRegistry
from delegation.runtime import DelegationRuntime
from middleware.guardrails import GuardrailsMiddleware
from middleware.human_review import build_interrupt_on
from middleware.trace import TraceMiddleware
from middleware.workflow_gate import WorkflowGateMiddleware
from project_store.checkpoint import create_checkpointer
from project_store.ledger import ProgressLedger
from traces.store import TraceStore
from workflows.loader import load_workflow

from .config import RuntimeConfig
from .context import AgentRuntimeContext


def create_write_agent(
    config: RuntimeConfig | None = None,
    *,
    deep_agent_factory: Callable[..., Any] | None = None,
    model: Any | None = None,
    checkpointer: Any | None = None,
    registry: AgentRegistry | None = None,
) -> Any:
    """Create the main writeAgent Deep Agent.

    `deep_agent_factory` is injectable for tests; production uses
    `deepagents.create_deep_agent` directly.
    """
    cfg = config or RuntimeConfig()
    cfg.ensure_dirs()
    workflow = load_workflow(cfg.skill_pack_root / "workflow.yaml")
    if not cfg.progress_path.exists():
        ProgressLedger.create(workflow.id, workflow.stage_ids).save(cfg.progress_path)
    trace_store = TraceStore(cfg.trace_path)
    delegation_runtime = DelegationRuntime(registry or AgentRegistry(), trace_store=trace_store)

    tools = _build_tools(cfg, trace_store, delegation_runtime)
    middleware = [
        WorkflowGateMiddleware(workflow, cfg.manifest_path, trace_store=trace_store, skill_pack_root=cfg.skill_pack_root),
        TraceMiddleware(trace_store),
        GuardrailsMiddleware(cfg.allowed_roots, repo_root=cfg.repo_root),
    ]
    creator = deep_agent_factory or _import_create_deep_agent()
    return creator(
        model=model if model is not None else cfg.model.model,
        tools=tools,
        system_prompt=(cfg.skill_pack_root / "system_prompt.md").read_text(encoding="utf-8"),
        middleware=middleware,
        skills=[str(cfg.skill_pack_root / "skills")],
        memory=[str(cfg.skill_pack_root / "references")],
        context_schema=AgentRuntimeContext,
        checkpointer=checkpointer or create_checkpointer(),
        interrupt_on=build_interrupt_on(),
        name="writeAgent",
    )


def _import_create_deep_agent() -> Callable[..., Any]:
    try:
        from deepagents import create_deep_agent
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("deepagents is required. Install requirements-orchestrator.txt.") from exc
    return create_deep_agent


def _build_tools(cfg: RuntimeConfig, trace_store: TraceStore, delegation_runtime: DelegationRuntime) -> list[Any]:
    from tools.ask_user import AskUserInput, ask_user
    from tools.execute_bash import ExecuteBashInput, execute_bash
    from tools.inspect_progress import inspect_progress
    from tools.update_artifact_manifest import UpdateArtifactManifestInput, update_artifact_manifest
    from tools.update_progress import UpdateProgressInput, update_progress
    from tools.delegate_to_agent import DelegateToAgentInput, delegate_to_agent

    def execute_bash_tool(command: str, cwd: str | None = None, timeout_sec: int = 60, purpose: str | None = None) -> dict[str, Any]:
        return execute_bash(
            command,
            cwd=cwd,
            timeout_sec=timeout_sec,
            purpose=purpose,
            repo_root=cfg.repo_root,
        ).model_dump()

    def update_artifact_manifest_tool(**kwargs: Any) -> dict[str, Any]:
        return update_artifact_manifest(cfg.manifest_path, trace_store=trace_store, **kwargs)

    def update_progress_tool(**kwargs: Any) -> dict[str, Any]:
        return update_progress(cfg.progress_path, trace_store=trace_store, **kwargs)

    def inspect_progress_tool() -> dict[str, Any]:
        return inspect_progress(cfg.progress_path, cfg.manifest_path)

    def delegate_to_agent_tool(**kwargs: Any) -> dict[str, Any]:
        return delegate_to_agent(delegation_runtime, **kwargs)

    return [
        StructuredTool.from_function(
            name="ask_user",
            description="Ask the user to provide missing requirement-analysis information.",
            func=ask_user,
            args_schema=AskUserInput,
        ),
        StructuredTool.from_function(
            name="execute_bash",
            description="Run a controlled command inside allowed project/workspace roots, primarily Skill scripts.",
            func=execute_bash_tool,
            args_schema=ExecuteBashInput,
        ),
        StructuredTool.from_function(
            name="update_artifact_manifest",
            description="Record or update business artifact metadata in ArtifactManifest.",
            func=update_artifact_manifest_tool,
            args_schema=UpdateArtifactManifestInput,
        ),
        StructuredTool.from_function(
            name="update_progress",
            description="Update the ProgressLedger stage status and artifact links.",
            func=update_progress_tool,
            args_schema=UpdateProgressInput,
        ),
        StructuredTool.from_function(
            name="inspect_progress",
            description="Inspect current workflow stage, blocked reason, and known artifacts.",
            func=inspect_progress_tool,
        ),
        StructuredTool.from_function(
            name="delegate_to_agent",
            description="Delegate work through the A2A-compatible delegation runtime.",
            func=delegate_to_agent_tool,
            args_schema=DelegateToAgentInput,
        ),
    ]
