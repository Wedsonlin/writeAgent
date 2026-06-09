"""Workflow gate integration for Deep Agents tool calls."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any, Awaitable, Callable

from langchain.agents.middleware import AgentMiddleware

from artifacts.manifest import ArtifactManifest
from traces.store import TraceStore
from workflows.gate import WorkflowGateDecision, can_execute_skill, evaluate_stage_gate
from workflows.loader import WorkflowDefinition


class WorkflowGateMiddleware(AgentMiddleware):
    name = "writeagent_workflow_gate"

    def __init__(
        self,
        workflow: WorkflowDefinition,
        manifest_path: str | Path | ArtifactManifest,
        *,
        trace_store: TraceStore | None = None,
        skill_pack_root: str | Path | None = None,
    ) -> None:
        self.workflow = workflow
        self.manifest_path = Path(manifest_path.path if isinstance(manifest_path, ArtifactManifest) else manifest_path)
        self.trace_store = trace_store
        self.skill_pack_root = Path(skill_pack_root).resolve() if skill_pack_root is not None else None

    def evaluate_stage(self, stage_id: str) -> WorkflowGateDecision:
        return evaluate_stage_gate(self.workflow, self._load_manifest(), stage_id)

    def evaluate_skill(self, skill_name: str) -> WorkflowGateDecision:
        return can_execute_skill(self.workflow, self._load_manifest(), skill_name)

    async def aevaluate_skill(self, skill_name: str) -> WorkflowGateDecision:
        return await asyncio.to_thread(self.evaluate_skill, skill_name)

    def wrap_tool_call(self, request: Any, handler: Callable[[Any], Any]) -> Any:
        if _request_name(request) != "execute_bash":
            return handler(request)

        args = _request_args(request)
        command = str(args.get("command", ""))
        cwd = args.get("cwd")
        skill_name = self._infer_skill_name(command, cwd)
        if skill_name is None:
            return handler(request)

        decision = self.evaluate_skill(skill_name)
        payload = {
            "skill_name": skill_name,
            "command": command,
            "cwd": cwd,
            "decision": decision.model_dump(),
        }
        if decision.status == "allowed":
            self._trace("workflow_gate_allowed", "allowed", payload)
            return handler(request)

        self._trace("workflow_gate_blocked", "blocked", payload)
        return _blocked_tool_message(request, skill_name, command, decision)

    async def awrap_tool_call(self, request: Any, handler: Callable[[Any], Awaitable[Any]]) -> Any:
        if _request_name(request) != "execute_bash":
            return await handler(request)

        args = _request_args(request)
        command = str(args.get("command", ""))
        cwd = args.get("cwd")
        skill_name = await asyncio.to_thread(self._infer_skill_name, command, cwd)
        if skill_name is None:
            return await handler(request)

        decision = await self.aevaluate_skill(skill_name)
        payload = {
            "skill_name": skill_name,
            "command": command,
            "cwd": cwd,
            "decision": decision.model_dump(),
        }
        if decision.status == "allowed":
            await self._atrace("workflow_gate_allowed", "allowed", payload)
            return await handler(request)

        await self._atrace("workflow_gate_blocked", "blocked", payload)
        return _blocked_tool_message(request, skill_name, command, decision)

    def _load_manifest(self) -> ArtifactManifest:
        return ArtifactManifest.load(self.manifest_path)

    def _infer_skill_name(self, command: str, cwd: Any) -> str | None:
        normalized_command = command.replace("\\", "/")
        match = re.search(r"skill_packs/[^\"'\s]+/skills/([^/]+)/scripts/run\.py", normalized_command)
        if match:
            return match.group(1)

        if "scripts/run.py" not in normalized_command and "run.py" not in normalized_command:
            return None

        if cwd is None:
            return None
        normalized_cwd = str(cwd).replace("\\", "/")
        match = re.search(r"skill_packs/[^\"'\s]+/skills/([^/\s]+)(?:/|$)", normalized_cwd)
        if match:
            return match.group(1)

        if self.skill_pack_root is None:
            return None
        try:
            cwd_path = Path(cwd)
            if not cwd_path.is_absolute():
                cwd_path = self.skill_pack_root.parent.parent / cwd_path
            relative = cwd_path.resolve().relative_to((self.skill_pack_root / "skills").resolve())
        except (OSError, ValueError):
            return None
        return relative.parts[0] if relative.parts else None

    def _trace(self, event_type: str, status: str, payload: dict[str, Any]) -> None:
        if self.trace_store is not None:
            self.trace_store.append(event_type, status=status, payload=payload)

    async def _atrace(self, event_type: str, status: str, payload: dict[str, Any]) -> None:
        if self.trace_store is not None:
            await asyncio.to_thread(self.trace_store.append, event_type, status=status, payload=payload)


def _request_name(request: Any) -> str | None:
    if hasattr(request, "name"):
        return getattr(request, "name")
    tool_call = getattr(request, "tool_call", None)
    if isinstance(tool_call, dict):
        return tool_call.get("name")
    tool = getattr(request, "tool", None)
    return getattr(tool, "name", None)


def _request_args(request: Any) -> dict[str, Any]:
    args = getattr(request, "args", None)
    if isinstance(args, dict):
        return args
    tool_call = getattr(request, "tool_call", None)
    if isinstance(tool_call, dict) and isinstance(tool_call.get("args"), dict):
        return tool_call["args"]
    return {}


def _tool_call_id(request: Any) -> str:
    tool_call_id = getattr(request, "tool_call_id", None)
    if isinstance(tool_call_id, str) and tool_call_id:
        return tool_call_id
    tool_call = getattr(request, "tool_call", None)
    if isinstance(tool_call, dict) and isinstance(tool_call.get("id"), str):
        return tool_call["id"]
    return "workflow_gate"


def _blocked_tool_message(
    request: Any,
    skill_name: str,
    command: str,
    decision: WorkflowGateDecision,
) -> Any:
    payload = {
        "status": "blocked",
        "reason": decision.reason,
        "skill_name": skill_name,
        "command": command,
        "missing_artifacts": decision.missing_artifacts,
        "next_recommended_stage": decision.next_recommended_stage,
    }
    try:
        from langchain_core.messages import ToolMessage
    except ImportError:  # pragma: no cover
        return payload
    return ToolMessage(content=json.dumps(payload, ensure_ascii=False), tool_call_id=_tool_call_id(request))
