"""Prompt builders for generic dynamic Sub-agents."""

from __future__ import annotations

import json
from typing import Any

from ..a2a.types import SubAgentSpec


SUBAGENT_SYSTEM_PROMPT = """You are a temporary dynamic Sub-agent in writeAgent.

You are not a fixed expert class. Your role, task, context, tools, output schema,
and success criteria are defined only by the SubAgentSpec.

Rules:
- Return structured JSON only.
- Do not call Skills.
- Do not delegate to another agent.
- Do not ask the user directly. If required information is missing, return
  status fields indicating needs_input and include followup_question.
- Do not write formal output fields. Your output is intermediate data for a
  deterministic Skill script to validate, format, render, and persist.
- Use only the context, Skill knowledge, and prompt templates explicitly
  included in the user prompt.
"""


def build_subagent_user_prompt(
    *,
    spec: SubAgentSpec,
    state_context: dict[str, Any],
    skill_context: dict[str, str],
    prompt_templates: dict[str, str],
) -> str:
    return "\n\n".join(
        [
            "SubAgentSpec:",
            json.dumps(
                {
                    "subagent_id": spec.subagent_id,
                    "role": spec.role,
                    "task": spec.task,
                    "input_keys": spec.input_keys,
                    "output_key": spec.output_key,
                    "success_criteria": spec.success_criteria,
                    "constraints": spec.constraints,
                },
                ensure_ascii=False,
                indent=2,
            ),
            "Allowed state context:",
            json.dumps(state_context, ensure_ascii=False, indent=2),
            "Allowed Skill context:",
            json.dumps(skill_context, ensure_ascii=False, indent=2),
            "Allowed prompt templates:",
            json.dumps(prompt_templates, ensure_ascii=False, indent=2),
            "Output requirements:",
            "Return one JSON object that satisfies the requested output schema. "
            "If the task output is naturally a list, wrap it in a named object field.",
        ]
    )


__all__ = ["SUBAGENT_SYSTEM_PROMPT", "build_subagent_user_prompt"]
