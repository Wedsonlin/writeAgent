"""Pure prompt rendering for workflow human clarification."""

from __future__ import annotations

from typing import Any


def ask_clarification(missing_info: list[dict[str, Any]]) -> str:
    """Render missing-info items into a user-facing question without an LLM call."""
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


__all__ = ["ask_clarification"]
