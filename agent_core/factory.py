"""Deep Agents factory for writeAgent."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable, Sequence
from langchain.tools import ToolRuntime
from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from delegation.discovery import AgentDiscovery
from delegation.registry import AgentRegistry
from middleware.guardrails import GuardrailsMiddleware
from middleware.trace import TraceMiddleware
from middleware.workflow_gate import WorkflowGateMiddleware
from project_store.checkpoint import create_checkpointer
from project_store.ledger import ProgressLedger
from traces.store import TraceStore
from workflows.loader import load_workflow

from .config import RuntimeConfig
from .context import AgentRuntimeContext
from .run_context import current_runtime_context_value


_CHECKPOINTER_DEFAULT = object()


class NoInputToolInput(BaseModel):
    """Empty schema for tools with no user-supplied arguments."""


def create_write_agent(
    config: RuntimeConfig | None = None,
    *,
    deep_agent_factory: Callable[..., Any] | None = None,
    model: Any | None = None,
    checkpointer: Any = _CHECKPOINTER_DEFAULT,
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
    discovered_agents = AgentDiscovery.load(
        cfg.agents_config_path,
        skill_pack_root=cfg.skill_pack_root,
        repo_root=cfg.repo_root,
    )
    # A2A delegation is intentionally disabled at runtime. Keep the registry
    # parameter for API compatibility while local specialists use Deep Agents
    # `task` routing exclusively.
    _ = registry or discovered_agents.registry

    tools = _build_tools(cfg, trace_store, workflow)
    middleware = _build_agent_middleware(
        cfg,
        workflow,
        trace_store,
        agent_scope="root",
        agent_name="writeAgent",
    )
    selected_model = model if model is not None else cfg.model.model
    if deep_agent_factory is None:
        _configure_general_purpose_subagent(selected_model, enabled=not discovered_agents.disable_general_purpose)
    creator = deep_agent_factory or _import_create_deep_agent()
    backend = _build_filesystem_backend(cfg)
    permissions = _build_filesystem_permissions()
    interrupt_on = _build_interrupt_on()
    subagents = _build_subagent_tree(
        discovered_agents.subagents,
        cfg,
        workflow,
        trace_store,
        tools=tools,
        model=selected_model,
        creator=creator,
        backend=backend,
        permissions=permissions,
        interrupt_on=interrupt_on,
        child_subagent_names=discovered_agents.child_subagent_names,
    )
    selected_checkpointer = create_checkpointer() if checkpointer is _CHECKPOINTER_DEFAULT else checkpointer
    return creator(
        model=selected_model,
        tools=tools,
        system_prompt=(cfg.skill_pack_root / "system_prompt.md").read_text(encoding="utf-8"),
        middleware=middleware,
        subagents=subagents,
        skills=[str(cfg.skill_pack_root / "skills")],
        memory=_build_memory_sources(cfg),
        permissions=permissions,
        backend=backend,
        context_schema=AgentRuntimeContext,
        checkpointer=selected_checkpointer,
        interrupt_on=interrupt_on,
        name="writeAgent",
    )


def _import_create_deep_agent() -> Callable[..., Any]:
    """
    create_deep_agent(
        model: str | BaseChatModel | None = None,
        tools: Sequence[BaseTool | Callable | dict[str, Any]] | None = None,
        *,
        system_prompt: str | SystemMessage | None = None,
        middleware: Sequence[AgentMiddleware] = (),
        subagents: Sequence[SubAgent | CompiledSubAgent | AsyncSubAgent] | None = None,
        skills: list[str] | None = None,
        memory: list[str] | None = None, # persistent context like AGENTS.md
        permissions: list[FilesystemPermission] | None = None,
        backend: BackendProtocol | BackendFactory | None = None,
        interrupt_on: dict[str, bool | InterruptOnConfig] | None = None,
        response_format: ... = None,
        state_schema: type[DeepAgentState] | None = None,
        context_schema: type[ContextT] | None = None,
        checkpointer: Checkpointer | None = None,
        store: BaseStore | None = None,
        debug: bool = False,
        name: str | None = None,
        cache: BaseCache | None = None,
    ) -> CompiledStateGraph  # return a pre-compiled langgraph graph
    """
    try:
        from deepagents import create_deep_agent
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("deepagents is required. Install requirements-orchestrator.txt.") from exc
    return create_deep_agent


def _configure_general_purpose_subagent(model: Any, *, enabled: bool) -> None:
    if enabled or not isinstance(model, str):
        return
    try:
        from deepagents import GeneralPurposeSubagentProfile, HarnessProfile, register_harness_profile
    except ImportError:  # pragma: no cover - optional when tests inject a fake factory
        return
    register_harness_profile(
        model,
        HarnessProfile(general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False)), # disable general purpose subagent
    )


def _build_agent_middleware(
    cfg: RuntimeConfig,
    workflow: Any,
    trace_store: TraceStore,
    *,
    agent_scope: str,
    agent_name: str,
) -> list[Any]:
    return [
        WorkflowGateMiddleware(
            workflow,
            cfg.manifest_path,
            trace_store=trace_store,
            skill_pack_root=cfg.skill_pack_root,
            runtime_config=cfg,
        ),
        TraceMiddleware(
            trace_store,
            runtime_config=cfg,
            agent_scope=agent_scope,
            agent_name=agent_name,
        ),
        GuardrailsMiddleware(cfg.allowed_roots, repo_root=cfg.repo_root),
    ]


def _with_subagent_middleware(
    subagents: Sequence[dict[str, Any]],
    cfg: RuntimeConfig,
    workflow: Any,
    trace_store: TraceStore,
) -> list[dict[str, Any]]:
    return [_enrich_subagent(subagent, cfg, workflow, trace_store) for subagent in subagents]


def _enrich_subagent(
    subagent: dict[str, Any],
    cfg: RuntimeConfig,
    workflow: Any,
    trace_store: TraceStore,
) -> dict[str, Any]:
    agent_name = str(subagent.get("name") or "subagent")
    existing_middleware = list(subagent.get("middleware", []))
    return {
        **subagent,
        "middleware": [
            *_build_agent_middleware(
                cfg,
                workflow,
                trace_store,
                agent_scope="subagent",
                agent_name=agent_name,
            ),
            *existing_middleware,
        ],
    }


def _strip_internal_subagent_keys(subagent: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in subagent.items() if key != "children"}


def _subagent_children(subagent: dict[str, Any]) -> list[str]:
    children = subagent.get("children") or []
    return [str(child) for child in children]


def _build_subagent_tree(
    subagents: Sequence[dict[str, Any]],
    cfg: RuntimeConfig,
    workflow: Any,
    trace_store: TraceStore,
    *,
    tools: Sequence[Any],
    model: Any,
    creator: Callable[..., Any],
    backend: Any,
    permissions: list[Any],
    interrupt_on: dict[str, object],
    child_subagent_names: set[str],
) -> list[dict[str, Any]]:
    by_name = {str(subagent["name"]): subagent for subagent in subagents}

    def build(name: str) -> dict[str, Any]:
        subagent = _enrich_subagent(by_name[name], cfg, workflow, trace_store)
        children = _subagent_children(subagent)
        if not children:
            return _strip_internal_subagent_keys(subagent)

        child_specs = [build(child_name) for child_name in children]
        runnable = creator(
            model=subagent.get("model", model),
            tools=tools,
            system_prompt=str(subagent["system_prompt"]),
            middleware=list(subagent.get("middleware", [])),
            subagents=child_specs,
            skills=list(subagent.get("skills") or []),
            permissions=permissions,
            backend=backend,
            context_schema=AgentRuntimeContext,
            interrupt_on=interrupt_on,
            name=str(subagent["name"]),
        )
        return {
            "name": str(subagent["name"]),
            "description": str(subagent["description"]),
            "runnable": runnable,
        }

    enriched: list[dict[str, Any]] = []
    for subagent in subagents:
        name = str(subagent["name"])
        if name in child_subagent_names:
            continue
        enriched.append(build(name))
    return enriched


def _build_tools(
    cfg: RuntimeConfig,
    trace_store: TraceStore,
    workflow: Any,
) -> list[Any]:
    from tools.ask_user import AskUserInput, ask_user
    from tools.execute_bash import ExecuteBashInput, execute_bash
    from tools.extract_sources import ExtractSourcesInput, aextract_sources, extract_sources
    from tools.inspect_progress import inspect_progress
    from tools.search_knowledge import SearchKnowledgeInput, asearch_knowledge, search_knowledge
    from tools.update_artifact_manifest import UpdateArtifactManifestInput, update_artifact_manifest
    from tools.update_progress import UpdateProgressInput, update_progress

    def execute_bash_tool(
        command: str,
        cwd: str | None = None,
        timeout_sec: int = 60,
        purpose: str | None = None,
        runtime: ToolRuntime | None = None,
    ) -> dict[str, Any]:
        project_cfg = _project_config_from_runtime(cfg, runtime)
        _ensure_project_state(project_cfg, workflow)
        return execute_bash(
            command,
            cwd=cwd,
            timeout_sec=timeout_sec,
            purpose=purpose,
            repo_root=project_cfg.repo_root,
        ).model_dump() # model_dump(): BaseModel -> dict

    def update_artifact_manifest_tool(runtime: ToolRuntime | None = None, **kwargs: Any) -> dict[str, Any]:
        project_cfg = _project_config_from_runtime(cfg, runtime)
        _ensure_project_state(project_cfg, workflow)
        kwargs = _normalize_manifest_paths(project_cfg, kwargs)
        return update_artifact_manifest(
            project_cfg.manifest_path,
            trace_store=_trace_store_for_project(project_cfg, trace_store),
            **kwargs,
        )

    def update_progress_tool(runtime: ToolRuntime | None = None, **kwargs: Any) -> dict[str, Any]:
        project_cfg = _project_config_from_runtime(cfg, runtime)
        _ensure_project_state(project_cfg, workflow)
        return update_progress(
            project_cfg.progress_path,
            trace_store=_trace_store_for_project(project_cfg, trace_store),
            **kwargs,
        )

    def inspect_progress_tool(runtime: ToolRuntime | None = None) -> dict[str, Any]:
        project_cfg = _project_config_from_runtime(cfg, runtime)
        _ensure_project_state(project_cfg, workflow)
        return inspect_progress(
            project_cfg.progress_path,
            project_cfg.manifest_path,
            project_id=project_cfg.project_id,
            project_root=_repo_virtual_path(project_cfg, project_cfg.project_root),
            artifact_root=_repo_virtual_path(project_cfg, project_cfg.artifact_root),
            tmp_root=_repo_virtual_path(project_cfg, project_cfg.tmp_root),
            evidence_root=_repo_virtual_path(project_cfg, project_cfg.evidence_root),
            cache_root=_repo_virtual_path(project_cfg, project_cfg.cache_root),
        )

    def search_knowledge_tool(runtime: ToolRuntime | None = None, **kwargs: Any) -> dict[str, Any]:
        project_cfg = _project_config_from_runtime(cfg, runtime)
        _ensure_project_state(project_cfg, workflow)
        return search_knowledge(
            artifact_root=project_cfg.project_root,
            manifest_path=project_cfg.manifest_path,
            **kwargs,
        )

    def extract_sources_tool(runtime: ToolRuntime | None = None, **kwargs: Any) -> dict[str, Any]:
        project_cfg = _project_config_from_runtime(cfg, runtime)
        _ensure_project_state(project_cfg, workflow)
        return extract_sources(
            artifact_root=project_cfg.project_root,
            manifest_path=project_cfg.manifest_path,
            **kwargs,
        )

    async def aexecute_bash_tool(
        command: str,
        cwd: str | None = None,
        timeout_sec: int = 60,
        purpose: str | None = None,
        runtime: ToolRuntime | None = None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            execute_bash_tool,
            command,
            cwd=cwd,
            timeout_sec=timeout_sec,
            purpose=purpose,
            runtime=runtime,
        )

    async def aupdate_artifact_manifest_tool(runtime: ToolRuntime | None = None, **kwargs: Any) -> dict[str, Any]:
        return await asyncio.to_thread(update_artifact_manifest_tool, runtime=runtime, **kwargs)

    async def aupdate_progress_tool(runtime: ToolRuntime | None = None, **kwargs: Any) -> dict[str, Any]:
        return await asyncio.to_thread(update_progress_tool, runtime=runtime, **kwargs)

    async def ainspect_progress_tool(runtime: ToolRuntime | None = None) -> dict[str, Any]:
        return await asyncio.to_thread(inspect_progress_tool, runtime=runtime)

    async def asearch_knowledge_tool(runtime: ToolRuntime | None = None, **kwargs: Any) -> dict[str, Any]:
        project_cfg = _project_config_from_runtime(cfg, runtime)
        await _ensure_project_state_async(project_cfg, workflow)
        return await asearch_knowledge(
            artifact_root=project_cfg.project_root,
            manifest_path=project_cfg.manifest_path,
            **kwargs,
        )

    async def aextract_sources_tool(runtime: ToolRuntime | None = None, **kwargs: Any) -> dict[str, Any]:
        project_cfg = _project_config_from_runtime(cfg, runtime)
        await _ensure_project_state_async(project_cfg, workflow)
        return await aextract_sources(
            artifact_root=project_cfg.project_root,
            manifest_path=project_cfg.manifest_path,
            **kwargs,
        )

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
            coroutine=aexecute_bash_tool,
            args_schema=ExecuteBashInput,
        ),
        StructuredTool.from_function(
            name="update_artifact_manifest",
            description="Record or update business artifact metadata in ArtifactManifest.",
            func=update_artifact_manifest_tool,
            coroutine=aupdate_artifact_manifest_tool,
            args_schema=UpdateArtifactManifestInput,
        ),
        StructuredTool.from_function(
            name="update_progress",
            description="Update the ProgressLedger stage status and artifact links.",
            func=update_progress_tool,
            coroutine=aupdate_progress_tool,
            args_schema=UpdateProgressInput,
        ),
        StructuredTool.from_function(
            name="inspect_progress",
            description="Inspect current workflow stage, blocked reason, and known artifacts.",
            func=inspect_progress_tool,
            coroutine=ainspect_progress_tool,
            args_schema=NoInputToolInput,
        ),
        StructuredTool.from_function(
            name="search_knowledge",
            description=(
                "Search Tavily for academic papers, web background, recent updates, or citation metadata. "
                "Use this before writing unsupported factual, timely, or citation-dependent content."
            ),
            func=search_knowledge_tool,
            coroutine=asearch_knowledge_tool,
            args_schema=SearchKnowledgeInput,
        ),
        StructuredTool.from_function(
            name="extract_sources",
            description="Extract source text from URLs selected from search evidence for citation and claim verification.",
            func=extract_sources_tool,
            coroutine=aextract_sources_tool,
            args_schema=ExtractSourcesInput,
        ),
    ]

def _build_interrupt_on() -> dict[str, object]:
    return {
        "ask_user": {"allowed_decisions": ["respond"]}, # return the human's message directly as the tool result, skipping execution, for "ask user" style tools
        # Whitelisted Skill scripts are already gated by GuardrailsMiddleware and WorkflowGateMiddleware.
        # Requiring HITL inside nested subagents blocks the workflow and surfaces as a subagent "error" in the UI.
        "execute_bash": False,
        "update_artifact_manifest": False,
        "update_progress": False,
        "inspect_progress": False,
        "search_knowledge": False,
        "extract_sources": False,
    }


def _project_config_from_runtime(cfg: RuntimeConfig, runtime: Any | None) -> RuntimeConfig:
    project_id = _runtime_context_value(runtime, "project_id")
    if project_id is None:
        project_id = current_runtime_context_value("project_id")
    if isinstance(project_id, str) and project_id.strip():
        return cfg.for_project(project_id)
    return cfg


def _runtime_context_value(runtime: Any | None, key: str) -> Any:
    if runtime is None:
        return None
    context = getattr(runtime, "context", None)
    if isinstance(context, dict):
        return context.get(key)
    return getattr(context, key, None)


def _ensure_project_state(project_cfg: RuntimeConfig, workflow: Any) -> None:
    project_cfg.ensure_dirs()
    if not project_cfg.progress_path.exists():
        ProgressLedger.create(workflow.id, workflow.stage_ids).save(project_cfg.progress_path)


async def _ensure_project_state_async(project_cfg: RuntimeConfig, workflow: Any) -> None:
    """Run project directory setup off the ASGI event loop."""
    await asyncio.to_thread(_ensure_project_state, project_cfg, workflow)


def _trace_store_for_project(project_cfg: RuntimeConfig, fallback: TraceStore) -> TraceStore:
    if project_cfg.trace_path == fallback.path:
        return fallback
    return TraceStore(project_cfg.trace_path)


def _repo_virtual_path(cfg: RuntimeConfig, path: Path) -> str:
    try:
        relative = path.resolve().relative_to(cfg.repo_root.resolve())
    except ValueError:
        return str(path)
    return "/" + relative.as_posix()


def _normalize_manifest_paths(cfg: RuntimeConfig, kwargs: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(kwargs)
    if isinstance(normalized.get("path"), str):
        normalized["path"] = _normalize_repo_path(cfg, normalized["path"])
    metadata = normalized.get("metadata")
    if isinstance(metadata, dict):
        normalized["metadata"] = {
            key: _normalize_repo_path(cfg, value) if key.endswith("_path") and isinstance(value, str) else value
            for key, value in metadata.items()
        }
    return normalized


def _normalize_repo_path(cfg: RuntimeConfig, raw_path: str) -> str:
    if raw_path.startswith("/.writeagent/") or raw_path.startswith("/case/") or raw_path.startswith("/skill_packs/"):
        return raw_path.lstrip("/")
    path = Path(raw_path)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(cfg.repo_root.resolve()).as_posix()
        except ValueError:
            return raw_path
    return raw_path.replace("\\", "/")


def _build_filesystem_backend(cfg: RuntimeConfig) -> Any:
    from deepagents.backends import FilesystemBackend

    return FilesystemBackend(root_dir=cfg.repo_root, virtual_mode=True)


def _build_filesystem_permissions() -> list[Any]:
    from deepagents.middleware.filesystem import FilesystemPermission

    return [
        FilesystemPermission(operations=["read"], paths=["/.env", "/.env.*"], mode="deny"),
        FilesystemPermission(
            operations=["write"],
            paths=["/.writeagent/projects", "/.writeagent/projects/**"],
            mode="allow",
        ),
        FilesystemPermission(operations=["write"], paths=["/**"], mode="deny"),
    ]


def _build_memory_sources(cfg: RuntimeConfig) -> list[str]:
    references_root = cfg.skill_pack_root / "references"
    if not references_root.exists():
        return []
    return [str(path) for path in sorted(references_root.rglob("*")) if path.is_file()]
