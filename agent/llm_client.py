"""LLM client for the orchestrator layer.

Internally delegates to ``skills._shared.llm`` so that orchestrator-side prompts
(e.g. ``human_clarify`` follow-up questions) use the exact same client as Skills.
This keeps configuration in one place (env vars) and avoids drift between modes.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# We add ``skills/`` to sys.path so that `_shared` resolves cleanly without
# turning Skills into an installed package (which would conflict with OpenClaw's
# self-contained skill-folder convention).
_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
if str(_SKILLS_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILLS_DIR))

from _shared.llm import chat, is_mock_mode, structured_json  # noqa: E402

__all__ = ["chat", "structured_json", "is_mock_mode", "ask_clarification"]


def ask_clarification(missing_info: list[dict[str, Any]]) -> str:
    """Render the missing-info list into a single chat question for the user.

    Returns the user-facing prompt string. The actual interaction is handled by
    ``nodes.human_clarify_node`` (which either reads from stdin in CLI mode or
    is interrupted by LangGraph for human-in-the-loop).
    """
    if not missing_info:
        return ""

    lines = ["以下信息缺失或不明确，请补充："]
    for idx, item in enumerate(missing_info, start=1):
        tag = {
            "blocker": "[必填]",
            "important": "[重要]",
            "nice-to-have": "[可选]",
        }.get(item.get("criticality", "important"), "[重要]")
        line = f"{idx}. {tag} {item.get('question', '')}"
        default = item.get("suggested_default")
        if default:
            line += f"（建议默认值：{default}）"
        lines.append(line)
    return "\n".join(lines)
