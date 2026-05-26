"""Render WritingTask → Markdown for human review."""

from __future__ import annotations

from typing import Any


def render_task_book(task: dict[str, Any], *, case_id: str = "") -> str:
    """Produce a Markdown rendering of the writing_task object."""
    lines: list[str] = []
    title = task.get("topic") or "（待定）"
    lines.append(f"# 论文写作任务书 · {title}")
    if case_id:
        lines.append(f"> case_id: `{case_id}`")
    lines.append("")

    lines.append("## 一、基本信息")
    lines.append("")
    lines.append(f"- 主题：{title}")
    lines.append(f"- 论文类型：{task.get('paper_type', '？')}")
    lines.append(f"- 写作语言：{task.get('language', 'zh')}")
    tj = task.get("target_journal", {}) or {}
    lines.append(f"- 目标期刊：{tj.get('name', '未指定')}（级别：{tj.get('level', '未指定')}）")
    style = tj.get("style_profile") or {}
    if style:
        lines.append(
            "- 期刊风格：引用 "
            f"`{style.get('citation_style', '?')}` · 语气 `{style.get('tone', '?')}` · "
            f"结构提示：{style.get('structure_hint', '?')}"
        )
    wl = task.get("word_limit", {}) or {}
    lines.append(f"- 总字数：{wl.get('total', '？')}")
    bc = wl.get("by_chapter") or {}
    if bc:
        bc_str = "，".join(f"{k}:{v}" for k, v in bc.items())
        lines.append(f"  - 各章节预算：{bc_str}")
    lines.append("")

    scope = task.get("research_scope") or {}
    if scope:
        lines.append("## 二、研究范围")
        lines.append("")
        if scope.get("domain"):
            lines.append(f"- 研究领域：{scope['domain']}")
        if scope.get("subtopics"):
            lines.append("- 子方向：")
            for s in scope["subtopics"]:
                lines.append(f"  - {s}")
        if scope.get("boundary"):
            lines.append(f"- 范围边界：{scope['boundary']}")
        lines.append("")

    lines.append("## 三、核心论点与创新点")
    lines.append("")
    for i, arg in enumerate(task.get("core_arguments", []), start=1):
        lines.append(f"{i}. {arg}")
    inn = task.get("innovation_points", []) or []
    if inn:
        lines.append("")
        lines.append("**创新点：**")
        for i, p in enumerate(inn, start=1):
            lines.append(f"- {p}")
    lines.append("")

    lines.append("## 四、章节框架")
    lines.append("")
    lines.append("| 章节 | 标题 | 字数预算 | 核心要点 |")
    lines.append("| --- | --- | --- | --- |")
    for ch in task.get("chapter_framework", []) or []:
        points = "；".join(ch.get("key_points", []) or [])
        lines.append(
            f"| {ch.get('chapter_id', '')} | {ch.get('title', '')} | "
            f"{ch.get('word_budget', '？')} | {points} |"
        )
    lines.append("")

    seeds = task.get("references_seed", []) or []
    if seeds:
        lines.append("## 五、初始参考文献种子")
        lines.append("")
        for s in seeds:
            lines.append(f"- [{s.get('type', '?')}] id=`{s.get('id', '?')}` path=`{s.get('path', '')}`")
        lines.append("")

    missing = task.get("missing_info", []) or []
    lines.append("## 六、待确认信息")
    lines.append("")
    if not missing:
        lines.append("（无关键缺失字段）")
    else:
        for m in missing:
            tag = {
                "blocker": "**[必填]**",
                "important": "[重要]",
                "nice-to-have": "[可选]",
            }.get(m.get("criticality", "important"), "[重要]")
            suggested = m.get("suggested_default")
            suggestion_txt = f"（建议默认：{suggested}）" if suggested else ""
            lines.append(f"- {tag} `{m.get('field', '')}`：{m.get('question', '')}{suggestion_txt}")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"
