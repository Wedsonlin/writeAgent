"""Render the LiteratureReport into a human-readable Markdown document."""

from __future__ import annotations

from typing import Any


def render_literature_report(
    report: dict[str, Any], *, case_id: str = "", topic: str = ""
) -> str:
    lines: list[str] = []
    head = topic or "文献梳理报告"
    lines.append(f"# 文献梳理报告 · {head}")
    if case_id:
        lines.append(f"> case_id: `{case_id}`")
    lines.append("")

    lines.append(f"- 关键词：{', '.join(report.get('keywords', []) or [])}")
    lines.append(f"- 引用风格：{report.get('citation_style', 'GB/T 7714')}")
    lines.append(f"- 文献条目：{len(report.get('papers', []))} 篇")
    lines.append("")

    landscape = report.get("research_landscape", {}) or {}
    clusters = landscape.get("clusters", []) or []
    timeline = landscape.get("timeline_summary", "")
    lines.append("## 一、研究脉络")
    lines.append("")
    if timeline:
        lines.append(f"> {timeline}")
        lines.append("")
    for c in clusters:
        lines.append(f"### {c.get('name', '?')}")
        lines.append("")
        summary = c.get("summary", "")
        if summary:
            lines.append(summary)
        ids = c.get("paper_ids", []) or []
        if ids:
            lines.append("")
            lines.append("代表性文献：")
            for pid in ids:
                lines.append(f"- `{pid}`")
        lines.append("")

    lines.append("## 二、共识 · 争议 · 研究缺口")
    lines.append("")
    lines.append("**共识：**")
    for c in report.get("consensus", []) or []:
        lines.append(f"- {c}")
    lines.append("")
    lines.append("**争议：**")
    for c in report.get("controversies", []) or []:
        lines.append(f"- {c}")
    lines.append("")
    lines.append("**研究缺口：**")
    for c in report.get("research_gaps", []) or []:
        lines.append(f"- {c}")
    lines.append("")

    lines.append("## 三、文献明细")
    lines.append("")
    lines.append("| ID | 年份 | 题目 | 作者 | 核心观点 | 证据强度 | 对齐 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for p in report.get("papers", []) or []:
        claims = "<br>".join(p.get("key_claims", []) or [])
        aligns = "<br>".join(
            f"#{a.get('core_argument_index', '?')} ({a.get('stance', '?')})"
            for a in p.get("alignment_to_core", []) or []
        )
        authors = "; ".join(p.get("authors", [])[:3])
        if len(p.get("authors", []) or []) > 3:
            authors += " 等"
        title = (p.get("title") or "").replace("|", "/")
        lines.append(
            f"| `{p.get('id', '')}` | {p.get('year', '?')} | {title} | "
            f"{authors} | {claims} | {p.get('evidence_strength', '?')} | {aligns} |"
        )
    lines.append("")

    bib = report.get("formatted_bibliography", {}) or {}
    lines.append("## 四、规范参考文献")
    lines.append("")
    lines.append("### GB/T 7714-2015")
    lines.append("")
    for i, item in enumerate(bib.get("gb7714", []) or [], start=1):
        lines.append(f"[{i}] {item}")
    lines.append("")
    lines.append("### APA 7")
    lines.append("")
    for item in bib.get("apa", []) or []:
        lines.append(f"- {item}")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"
