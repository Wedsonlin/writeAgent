"""Generic runtime for dynamically derived Sub-agents."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..a2a.schemas import load_output_schema, validate_json_schema
from ..a2a.types import SubAgentResult, SubAgentSpec, SubAgentTrace
from ..a2a.validator import errors_to_dicts, validate_subagent_spec
from ..llm_gateway import LLMGateway
from ..state_store import StateStore
from ..trace_store import TraceStore, now_iso
from .policy import merged_constraints
from .prompts import SUBAGENT_SYSTEM_PROMPT, build_subagent_user_prompt


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"


class SubAgentRuntime:
    """Execute one SubAgentSpec as a single structured-json reasoning call."""

    def __init__(
        self,
        *,
        llm_gateway: LLMGateway,
        state_store: StateStore | None = None,
        trace_store: TraceStore | None = None,
        repo_root: Path = REPO_ROOT,
    ) -> None:
        self.llm_gateway = llm_gateway
        self.state_store = state_store or StateStore()
        self.trace_store = trace_store
        self.repo_root = Path(repo_root)

    def run(self, spec: SubAgentSpec, state_path: Path) -> SubAgentResult:
        started_at = now_iso()
        constraints = merged_constraints(spec)
        spec.constraints = dict(constraints)
        trace = SubAgentTrace(
            subagent_id=spec.subagent_id,
            parent_agent_id=spec.parent_agent_id,
            role=spec.role,
            task=spec.task,
            input_keys=spec.input_keys,
            output_key=spec.output_key,
            skill_context=spec.skill_context,
            prompt_refs=spec.prompt_refs,
            allowed_tools=spec.allowed_tools,
            constraints=spec.constraints,
            status="running",
            started_at=started_at,
        )

        try:
            spec_errors = validate_subagent_spec(spec, workspace_root=self.repo_root)
            if spec_errors:
                return self._finish_failed(trace, spec, errors_to_dicts(spec_errors))

            state_context = self.state_store.extract(
                Path(state_path),
                spec.input_keys,
                max_context_chars=int(spec.constraints.get("max_context_chars", 30000)),
            )
            skill_context = self._read_skill_context(spec)
            prompt_templates = self._read_prompt_templates(spec)
            schema = load_output_schema(spec.output_schema)
            payload = self.llm_gateway.structured_json(
                caller=spec.subagent_id,
                system_prompt=SUBAGENT_SYSTEM_PROMPT,
                user_prompt=build_subagent_user_prompt(
                    spec=spec,
                    state_context=state_context,
                    skill_context=skill_context,
                    prompt_templates=prompt_templates,
                ),
                output_schema=schema or spec.output_schema,
                call_type="subagent_structured_json",
                model_policy=spec.model_policy,
                temperature=float(spec.model_policy.get("temperature", 0.2)),
                mock_payload=self._mock_payload(spec),
            )

            if payload.get("needs_input") is True or payload.get("status") == "needs_input":
                result = SubAgentResult(
                    subagent_id=spec.subagent_id,
                    parent_agent_id=spec.parent_agent_id,
                    status="needs_input",
                    output_key=None,
                    result_summary=str(payload.get("result_summary") or "Sub-agent needs more input."),
                    needs_followup=True,
                    followup_question=str(payload.get("followup_question") or ""),
                )
                return self._finish(trace, result)

            schema_errors = validate_json_schema(payload, schema)
            if schema_errors:
                return self._finish_failed(trace, spec, schema_errors)

            output_text = json.dumps(payload, ensure_ascii=False)
            max_output_chars = int(spec.constraints.get("max_output_chars", 50000))
            if len(output_text) > max_output_chars:
                return self._finish_failed(
                    trace,
                    spec,
                    [{"code": "max_output_chars", "message": "Sub-agent output exceeds max_output_chars.", "detail": {"max_output_chars": max_output_chars}}],
                )

            artifacts: list[dict[str, Any]] = []
            if spec.write_policy == "write_intermediate":
                self.state_store.write_intermediate(Path(state_path), spec.output_key, payload)
                artifacts.append({"kind": "state_json_path", "uri": f"state.json#{spec.output_key}"})

            result = SubAgentResult(
                subagent_id=spec.subagent_id,
                parent_agent_id=spec.parent_agent_id,
                status="completed",
                output_key=spec.output_key if spec.write_policy == "write_intermediate" else None,
                result_summary=str(payload.get("result_summary") or f"Completed {spec.role}: {spec.task[:120]}"),
                artifacts=artifacts,
                usage={"output_chars": len(output_text)},
            )
            return self._finish(trace, result)
        except Exception as exc:  # noqa: BLE001 - return structured failure to Main Agent.
            return self._finish_failed(trace, spec, [{"code": "runtime_error", "message": str(exc), "detail": {}}])

    def _read_skill_context(self, spec: SubAgentSpec) -> dict[str, str]:
        contexts: dict[str, str] = {}
        for skill_name in spec.skill_context:
            path = SKILLS_DIR / skill_name / "SKILL.md"
            if path.exists():
                contexts[skill_name] = path.read_text(encoding="utf-8")
        return contexts

    def _read_prompt_templates(self, spec: SubAgentSpec) -> dict[str, str]:
        prompts: dict[str, str] = {}
        for prompt_ref in spec.prompt_refs:
            path = (self.repo_root / prompt_ref).resolve()
            path.relative_to(self.repo_root.resolve())
            if path.exists() and path.is_file():
                prompts[prompt_ref] = path.read_text(encoding="utf-8")
        return prompts

    def _finish_failed(self, trace: SubAgentTrace, spec: SubAgentSpec, errors: list[dict[str, Any]]) -> SubAgentResult:
        result = SubAgentResult(
            subagent_id=spec.subagent_id,
            parent_agent_id=spec.parent_agent_id,
            status="failed",
            output_key=None,
            result_summary="Sub-agent execution failed.",
            errors=errors,
        )
        return self._finish(trace, result)

    def _finish(self, trace: SubAgentTrace, result: SubAgentResult) -> SubAgentResult:
        trace.status = result.status
        trace.ended_at = now_iso()
        trace.result_summary = result.result_summary
        trace.errors = list(result.errors)
        if self.trace_store is not None:
            self.trace_store.append_subagent_trace(asdict(trace))
        return result

    def _mock_payload(self, spec: SubAgentSpec) -> dict[str, Any]:
        if spec.output_key.endswith("raw_writing_task"):
            return {
                "topic": "EMI 技术用于 CFRP 损伤检测",
                "paper_type": "survey",
                "language": "zh",
                "target_journal": {"name": "未指定", "level": "未指定"},
                "word_limit": {"total": 8000},
                "core_arguments": ["EMI 技术可作为 CFRP 层合板损伤检测的有效无损监测方法。"],
                "innovation_points": [],
                "research_scope": {"domain": "CFRP structural health monitoring", "subtopics": ["EMI", "damage detection"], "boundary": ""},
                "chapter_framework": [],
                "references_seed": [],
                "missing_info": [],
            }
        if spec.output_key.endswith("paper_claims"):
            return {"paper_claims": []}
        if spec.output_key.endswith("synthesis"):
            return {
                "clusters": [],
                "timeline_summary": "",
                "consensus": [],
                "controversies": [],
                "research_gaps": [],
                "alignments": [],
            }
        if spec.output_key.endswith("raw_outline"):
            return {
                "total_word_budget": 8000,
                "sections": [
                    {
                        "id": "1",
                        "title": "引言",
                        "level": 1,
                        "parent_id": None,
                        "key_points": ["研究背景", "问题定义", "论文结构"],
                        "transition_note": "",
                        "word_budget": 1000,
                        "supporting_papers": [],
                    }
                ],
            }
        if spec.output_key.endswith("raw_draft"):
            return {
                "abstract": "本文围绕 CFRP 损伤检测展开综述。",
                "keywords": ["CFRP", "EMI", "损伤检测"],
                "sections": [
                    {
                        "id": "1",
                        "title": "引言",
                        "content_markdown": "CFRP 损伤检测是结构健康监测的重要问题。",
                        "citations_used": [],
                        "word_count": 30,
                    }
                ],
                "open_questions": [],
            }
        if spec.output_key.endswith("raw_format_report"):
            return {
                "normalized_draft": {
                    "abstract": "本文围绕 CFRP 损伤检测展开综述。",
                    "sections": [],
                },
                "export_paths": {},
                "issues": [],
            }
        if spec.output_key.endswith("raw_polish_report"):
            return {
                "polished_draft": {
                    "abstract": "本文围绕 CFRP 损伤检测展开综述。",
                    "sections": [],
                },
                "polish_log": [],
                "plagiarism_optimization": [],
            }
        return {"result_summary": f"Mock output for {spec.role}.", "items": []}


__all__ = ["SubAgentRuntime"]
