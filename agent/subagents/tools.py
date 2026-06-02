"""Restricted tools available to dynamic Sub-agents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..a2a.types import SubAgentSpec
from ..llm_gateway import LLMGateway
from ..state_store import StateStore, summarize_value
from .policy import assert_allowed_tool, assert_prompt_ref_allowed


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"


class RestrictedSubagentTools:
    """Tool facade that enforces SubAgentSpec authorization on every call."""

    def __init__(
        self,
        *,
        spec: SubAgentSpec,
        state_store: StateStore,
        llm_gateway: LLMGateway,
        repo_root: Path = REPO_ROOT,
    ) -> None:
        self.spec = spec
        self.state_store = state_store
        self.llm_gateway = llm_gateway
        self.repo_root = Path(repo_root)

    def inspect_state_subset(self, state_path: Path) -> dict[str, Any]:
        assert_allowed_tool(self.spec, "inspect_state_subset")
        max_chars = int(self.spec.constraints.get("max_context_chars", 30000))
        return self.state_store.extract(state_path, self.spec.input_keys, max_context_chars=max_chars)

    def read_skill_prompt(self, prompt_ref: str) -> str:
        assert_allowed_tool(self.spec, "read_skill_prompt")
        path = assert_prompt_ref_allowed(self.spec, prompt_ref, self.repo_root)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Prompt ref not found: {prompt_ref}")
        return path.read_text(encoding="utf-8")

    def read_skill_context(self, skill_name: str) -> str:
        assert_allowed_tool(self.spec, "read_skill_context")
        if skill_name not in self.spec.skill_context:
            raise PermissionError(f"Skill context is not authorized: {skill_name}")
        path = SKILLS_DIR / skill_name / "SKILL.md"
        if not path.exists():
            raise FileNotFoundError(f"Skill context not found: {skill_name}")
        return path.read_text(encoding="utf-8")

    def summarize_context(self, context: dict[str, Any]) -> dict[str, Any]:
        assert_allowed_tool(self.spec, "summarize_context")
        payload = json.dumps(context, ensure_ascii=False)
        if len(payload) <= int(self.spec.constraints.get("max_context_chars", 30000)):
            return context
        summary = self.llm_gateway.structured_json(
            caller=self.spec.subagent_id,
            system_prompt="Summarize the provided JSON context as compact structured JSON.",
            user_prompt=payload,
            output_schema={"type": "object"},
            call_type="subagent_tool_summarize_context",
            model_policy=self.spec.model_policy,
            mock_payload={"summary": summarize_value(context, max_text=1000)},
        )
        return summary


__all__ = ["RestrictedSubagentTools"]
