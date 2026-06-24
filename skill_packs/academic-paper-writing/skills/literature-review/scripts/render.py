from __future__ import annotations

from typing import Any


def render_literature_report_markdown(report: dict[str, Any]) -> str:
    sections = report.get("report_sections", {})
    lines: list[str] = ["# 文献梳理报告", ""]
    _append_task_alignment(lines, sections.get("task_alignment", {}))
    _append_list_section(lines, "研究现状", sections.get("research_status"))
    _append_field_context(lines, sections.get("field_context", {}))
    _append_viewpoints(lines, sections.get("core_literature_viewpoints", []))
    _append_support_matrices(lines, sections.get("argument_support_matrix", []), sections.get("innovation_support_matrix", []))
    _append_gaps_and_supplement(lines, sections.get("research_gaps"), sections.get("supplement_search_summary", {}))
    _append_unmapped(lines, report.get("unmapped_papers", []))
    _append_references(lines, sections.get("references", {}))
    return "\n".join(lines).rstrip() + "\n"


def _append_task_alignment(lines: list[str], alignment: dict[str, Any]) -> None:
    lines.extend(["## 任务书对齐目标", ""])
    if not isinstance(alignment, dict):
        lines.extend(["- 暂无任务书对齐信息。", ""])
        return
    topic = str(alignment.get("topic") or "").strip()
    if topic:
        lines.append(f"- 主题：{topic}")
    core_arguments = _list(alignment.get("core_arguments"))
    if core_arguments:
        lines.append("- 核心论点：")
        lines.extend(f"  - 核心论点 {idx}：{item}" for idx, item in enumerate(core_arguments, start=1))
    innovation_points = _list(alignment.get("innovation_points"))
    if innovation_points:
        lines.append("- 创新点：")
        lines.extend(f"  - 创新点 {idx}：{item}" for idx, item in enumerate(innovation_points, start=1))
    if not topic and not core_arguments and not innovation_points:
        lines.append("- 暂无任务书对齐信息。")
    lines.append("")


def _append_list_section(lines: list[str], title: str, values: Any) -> None:
    lines.extend([f"## {title}", ""])
    items = _list(values)
    if not items:
        lines.extend(["- 暂无明确条目。", ""])
        return
    lines.extend(f"- {item}" for item in items)
    lines.append("")


def _append_field_context(lines: list[str], context: dict[str, Any]) -> None:
    lines.extend(["## 领域脉络", ""])
    clusters = context.get("clusters") if isinstance(context, dict) else []
    if clusters:
        for cluster in clusters:
            if not isinstance(cluster, dict):
                continue
            name = str(cluster.get("name") or "未命名主题").strip()
            summary = str(cluster.get("summary") or "").strip()
            paper_ids = ", ".join(str(item) for item in cluster.get("paper_ids", []) if str(item))
            suffix = f"（{paper_ids}）" if paper_ids else ""
            lines.append(f"- **{name}**：{summary}{suffix}")
    else:
        lines.append("- 暂无明确主题簇。")
    timeline = str(context.get("timeline_summary") or "").strip() if isinstance(context, dict) else ""
    if timeline:
        lines.extend(["", f"时间线概述：{timeline}"])
    lines.append("")


def _append_viewpoints(lines: list[str], viewpoints: Any) -> None:
    lines.extend(["## 核心文献观点", ""])
    items = [item for item in viewpoints if isinstance(item, dict)] if isinstance(viewpoints, list) else []
    if not items:
        lines.extend(["- 暂无已映射核心文献观点。", ""])
        return
    for item in items:
        title = str(item.get("title") or item.get("paper_id") or "Untitled").strip()
        year = item.get("year") or "n.d."
        paper_id = item.get("paper_id") or ""
        strength = item.get("evidence_strength") or "weak"
        lines.append(f"- **{title}**（{year}，{paper_id}，证据强度：{strength}）")
        claims = _list(item.get("key_claims"))
        for claim in claims:
            lines.append(f"  - {claim}")
    lines.append("")


def _append_support_matrices(lines: list[str], arguments: Any, innovations: Any) -> None:
    lines.extend(["## 论点与创新点支撑矩阵", ""])
    _append_support_matrix(lines, "核心论点", arguments, "argument")
    _append_support_matrix(lines, "创新点", innovations, "innovation")
    lines.append("")


def _append_support_matrix(lines: list[str], label: str, matrix: Any, target_key: str) -> None:
    items = [item for item in matrix if isinstance(item, dict)] if isinstance(matrix, list) else []
    if not items:
        lines.append(f"- 暂无{label}支撑矩阵。")
        return
    for item in items:
        index = int(item.get("index") or 0) + 1
        target = str(item.get(target_key) or "").strip()
        strength = item.get("support_strength") or "weak"
        papers = ", ".join(str(paper) for paper in item.get("supporting_papers", []) if str(paper)) or "暂无直接支撑文献"
        gap = str(item.get("gap") or "").strip()
        lines.append(f"- {label} {index}：{target}")
        lines.append(f"  - 支撑强度：{strength}")
        lines.append(f"  - 支撑文献：{papers}")
        summaries = _list(item.get("evidence_summaries"))
        for summary in summaries:
            lines.append(f"  - 证据摘要：{summary}")
        if gap:
            lines.append(f"  - 缺口：{gap}")


def _append_gaps_and_supplement(lines: list[str], gaps: Any, summary: dict[str, Any]) -> None:
    lines.extend(["## 研究缺口与补充检索", ""])
    items = _list(gaps)
    if items:
        lines.extend(f"- {item}" for item in items)
    else:
        lines.append("- 暂无明确研究缺口。")
    if isinstance(summary, dict) and summary:
        status = summary.get("status") or "unknown"
        rendered_summary = summary.get("summary") or summary.get("reason") or ""
        lines.append(f"- 补充检索状态：{status}")
        if rendered_summary:
            lines.append(f"- 补充检索说明：{rendered_summary}")
        uncovered_arguments = _list(summary.get("uncovered_arguments"))
        uncovered_innovations = _list(summary.get("uncovered_innovations"))
        if uncovered_arguments:
            lines.append("- 未覆盖核心论点：")
            lines.extend(f"  - {item}" for item in uncovered_arguments)
        if uncovered_innovations:
            lines.append("- 未覆盖创新点：")
            lines.extend(f"  - {item}" for item in uncovered_innovations)
    lines.append("")


def _append_unmapped(lines: list[str], unmapped: Any) -> None:
    items = _list(unmapped)
    if not items:
        return
    lines.extend(["## 未映射文献", ""])
    lines.extend(f"- {item}" for item in items)
    lines.append("")


def _append_references(lines: list[str], references: dict[str, Any]) -> None:
    lines.extend(["## 参考文献", "", "### GB/T 7714", ""])
    gb_items = _list(references.get("gb7714") if isinstance(references, dict) else [])
    lines.extend(f"{idx}. {item}" for idx, item in enumerate(gb_items, start=1))
    if not gb_items:
        lines.append("暂无。")
    lines.extend(["", "### APA", ""])
    apa_items = _list(references.get("apa") if isinstance(references, dict) else [])
    lines.extend(f"{idx}. {item}" for idx, item in enumerate(apa_items, start=1))
    if not apa_items:
        lines.append("暂无。")
    lines.append("")


def _list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None and str(item)]
    return [str(value)]
