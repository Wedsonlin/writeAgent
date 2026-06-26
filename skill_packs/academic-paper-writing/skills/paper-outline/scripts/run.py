from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def main() -> int:
    args = _parse()
    data = _load(args.input)
    outline = _build_outline(data)
    markdown = _render_markdown(outline)
    output_path = Path(args.output)
    markdown_path = output_path.with_suffix(".md")
    payload = {
        "artifact_type": "outline",
        "outline": outline,
        "outline_markdown": markdown,
        "outline_markdown_path": str(markdown_path),
    }
    _write(output_path, payload)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown, encoding="utf-8")
    return 0


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def _load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(path: str | Path, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_outline(data: dict[str, Any]) -> dict[str, Any]:
    task = _object(data.get("writing_task"))
    report = _unwrap_report(data.get("literature_report"))
    topic = str(task.get("topic") or "未命名论文")
    paper_type = _paper_type(task)
    arguments = _strings(task.get("core_arguments"))
    innovations = _strings(task.get("innovation_points"))
    total = _total_words(task)
    framework = _framework(task, paper_type)
    argument_support = _matrix_by_key(report.get("argument_support_matrix"), "argument")
    innovation_support = _matrix_by_key(report.get("innovation_support_matrix"), "innovation")

    top_sections = _top_sections(framework, paper_type)
    budgets = _allocate_top_budgets(top_sections, total)
    sections = _sections(
        top_sections=top_sections,
        budgets=budgets,
        arguments=arguments,
        innovations=innovations,
        argument_support=argument_support,
        innovation_support=innovation_support,
        report=report,
    )
    argument_coverage = _coverage(arguments, argument_support, sections, "argument")
    innovation_coverage = _coverage(innovations, innovation_support, sections, "innovation")
    quality_flags = _quality_flags(
        paper_type=paper_type,
        sections=sections,
        argument_coverage=argument_coverage,
        innovation_coverage=innovation_coverage,
        total=total,
        budgets=budgets,
    )

    return {
        "topic": topic,
        "paper_type": paper_type,
        "total_word_budget": total,
        "structure_rationale": _structure_rationale(paper_type),
        "sections": sections,
        "logic_graph": _logic_graph(sections),
        "argument_coverage": argument_coverage,
        "innovation_coverage": innovation_coverage,
        "word_budget_plan": [
            {"section_id": section["section_id"], "title": section["title"], "word_budget": section["word_budget"]}
            for section in sections
            if section["level"] == 1
        ],
        "quality_flags": quality_flags,
    }


def _unwrap_report(value: Any) -> dict[str, Any]:
    report = _object(value)
    nested = report.get("literature_report")
    if isinstance(nested, dict):
        return nested
    return report


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _paper_type(task: dict[str, Any]) -> str:
    raw = str(task.get("paper_type") or task.get("research_type") or "survey").lower()
    if raw in {"review", "survey", "综述", "literature review"}:
        return "survey"
    if raw in {"empirical", "experiment", "实证"}:
        return "empirical"
    if raw in {"theoretical", "theory", "理论"}:
        return "theoretical"
    return raw or "survey"


def _total_words(task: dict[str, Any]) -> int:
    word_limit = _object(task.get("word_limit"))
    try:
        return int(word_limit.get("total") or task.get("total_word_budget") or 8000)
    except (TypeError, ValueError):
        return 8000


def _framework(task: dict[str, Any], paper_type: str) -> list[dict[str, Any]]:
    framework = [item for item in _list(task.get("chapter_framework")) if isinstance(item, dict)]
    if framework:
        return framework
    if paper_type == "empirical":
        titles = ["引言", "相关工作", "方法", "实验设计", "结果与讨论", "结论"]
    elif paper_type == "theoretical":
        titles = ["引言", "相关研究", "理论框架", "命题与模型", "分析与讨论", "结论"]
    else:
        titles = ["引言", "研究现状与领域脉络", "主题比较与综合", "研究缺口与未来趋势", "结论"]
    return [{"chapter_id": str(index + 1), "title": title, "key_points": []} for index, title in enumerate(titles)]


def _top_sections(framework: list[dict[str, Any]], paper_type: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = [
        {"section_id": "abstract", "title": "摘要", "key_points": ["研究背景", "核心论点", "主要结论"]}
    ]
    for index, item in enumerate(framework, start=1):
        title = str(item.get("title") or f"第{index}章")
        sections.append(
            {
                "section_id": str(item.get("chapter_id") or index),
                "title": title,
                "key_points": _strings(item.get("key_points")) or _default_key_points(title, paper_type),
            }
        )
    if not any("结论" in section["title"] for section in sections):
        sections.append({"section_id": "conclusion", "title": "结论", "key_points": ["主要发现", "理论与工程启示"]})
    sections.append({"section_id": "references", "title": "参考文献", "key_points": []})
    return sections


def _default_key_points(title: str, paper_type: str) -> list[str]:
    if "引言" in title:
        return ["研究背景", "问题定义", "本文贡献"]
    if "现状" in title or "脉络" in title:
        return ["研究现状", "领域脉络", "代表性工作"]
    if "缺口" in title or "趋势" in title or "挑战" in title:
        return ["研究缺口", "关键挑战", "未来趋势"]
    if paper_type == "survey":
        return ["主题划分", "代表系统", "综合比较"]
    return ["章节目标", "方法或观点", "小结"]


def _allocate_top_budgets(top_sections: list[dict[str, Any]], total: int) -> dict[str, int]:
    positive = [section for section in top_sections if section["section_id"] != "references"]
    weights = [_weight(section["title"], section["section_id"]) for section in positive]
    weight_sum = sum(weights) or 1.0
    raw = [max(120, int(total * weight / weight_sum)) for weight in weights]
    diff = total - sum(raw)
    raw[-1] += diff
    return {
        **{section["section_id"]: budget for section, budget in zip(positive, raw)},
        "references": 0,
    }


def _weight(title: str, section_id: str) -> float:
    if section_id == "abstract":
        return 0.55
    if "引言" in title:
        return 1.25
    if "现状" in title or "脉络" in title:
        return 1.85
    if "比较" in title or "基础设施" in title or "系统" in title or "框架" in title:
        return 2.25
    if "缺口" in title or "趋势" in title or "挑战" in title or "讨论" in title:
        return 1.55
    if "结论" in title:
        return 0.75
    return 1.45


def _sections(
    *,
    top_sections: list[dict[str, Any]],
    budgets: dict[str, int],
    arguments: list[str],
    innovations: list[str],
    argument_support: dict[str, dict[str, Any]],
    innovation_support: dict[str, dict[str, Any]],
    report: dict[str, Any],
) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    body_ids: list[str] = []
    for index, top in enumerate(top_sections):
        section_id = top["section_id"]
        title = top["title"]
        linked_arguments, linked_innovations = _linked_items(title, index, arguments, innovations, argument_support, innovation_support)
        if section_id not in {"abstract", "references"}:
            body_ids.append(section_id)
        section = _section(
            section_id=section_id,
            level=1,
            title=title,
            parent_id=None,
            word_budget=budgets.get(section_id, 0),
            key_points=top.get("key_points", []),
            linked_arguments=linked_arguments,
            linked_innovations=linked_innovations,
            argument_support=argument_support,
            innovation_support=innovation_support,
            report=report,
        )
        sections.append(section)
        key_points = _strings(top.get("key_points"))
        child_budget = _split_budget(section["word_budget"], len(key_points))
        for child_index, point in enumerate(key_points, start=1):
            child_id = f"{section_id}.{child_index}"
            sections.append(
                _section(
                    section_id=child_id,
                    level=2,
                    title=point,
                    parent_id=section_id,
                    word_budget=child_budget[child_index - 1] if child_budget else 0,
                    key_points=[point],
                    linked_arguments=linked_arguments,
                    linked_innovations=linked_innovations,
                    argument_support=argument_support,
                    innovation_support=innovation_support,
                    report=report,
                )
            )
    _ensure_coverage(sections, body_ids, arguments, "linked_core_arguments")
    _ensure_coverage(sections, body_ids, innovations, "linked_innovation_points")
    for section in sections:
        section["supporting_papers"] = _supporting_papers(section["linked_core_arguments"], section["linked_innovation_points"], argument_support, innovation_support)
        section["evidence_notes"] = _evidence_notes(section["linked_core_arguments"], section["linked_innovation_points"], argument_support, innovation_support, report)
    return sections


def _section(
    *,
    section_id: str,
    level: int,
    title: str,
    parent_id: str | None,
    word_budget: int,
    key_points: list[str],
    linked_arguments: list[str],
    linked_innovations: list[str],
    argument_support: dict[str, dict[str, Any]],
    innovation_support: dict[str, dict[str, Any]],
    report: dict[str, Any],
) -> dict[str, Any]:
    role = _role(title, level)
    supporting_papers = _supporting_papers(linked_arguments, linked_innovations, argument_support, innovation_support)
    evidence_notes = _evidence_notes(linked_arguments, linked_innovations, argument_support, innovation_support, report)
    transition = _transition(title)
    return {
        "section_id": section_id,
        "id": section_id,
        "level": level,
        "title": title,
        "parent_id": parent_id,
        "word_budget": int(word_budget),
        "rhetorical_role": role,
        "core_points": key_points,
        "key_points": key_points,
        "linked_core_arguments": linked_arguments,
        "linked_innovation_points": linked_innovations,
        "supporting_papers": supporting_papers,
        "evidence_notes": evidence_notes,
        "transition_in": "承接上一部分的问题或结论，进入本节论证重点。" if level == 1 else "承接本章主题展开具体要点。",
        "transition_out": transition,
        "transition_note": transition,
    }


def _linked_items(
    title: str,
    index: int,
    arguments: list[str],
    innovations: list[str],
    argument_support: dict[str, dict[str, Any]],
    innovation_support: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str]]:
    if "摘要" in title or "参考文献" in title:
        return [], []
    weak_arguments = [item for item in arguments if _strength(argument_support.get(item)) == "weak"]
    weak_innovations = [item for item in innovations if _strength(innovation_support.get(item)) == "weak"]
    if any(marker in title for marker in ["缺口", "趋势", "挑战", "讨论"]):
        return weak_arguments or arguments[-1:], weak_innovations or innovations[-1:]
    if "引言" in title:
        return arguments[:2], innovations[:1]
    argument = arguments[(index - 1) % len(arguments)] if arguments else None
    innovation = innovations[(index - 1) % len(innovations)] if innovations else None
    return ([argument] if argument else []), ([innovation] if innovation else [])


def _ensure_coverage(sections: list[dict[str, Any]], body_ids: list[str], items: list[str], field: str) -> None:
    if not body_ids:
        return
    body_sections = [section for section in sections if section["section_id"] in body_ids]
    for index, item in enumerate(items):
        if any(item in section[field] for section in body_sections):
            continue
        target = body_sections[index % len(body_sections)]
        target[field].append(item)


def _supporting_papers(
    arguments: list[str],
    innovations: list[str],
    argument_support: dict[str, dict[str, Any]],
    innovation_support: dict[str, dict[str, Any]],
) -> list[str]:
    papers: list[str] = []
    for item in arguments:
        papers.extend(_strings(_object(argument_support.get(item)).get("supporting_papers")))
    for item in innovations:
        papers.extend(_strings(_object(innovation_support.get(item)).get("supporting_papers")))
    return _dedupe(papers)


def _evidence_notes(
    arguments: list[str],
    innovations: list[str],
    argument_support: dict[str, dict[str, Any]],
    innovation_support: dict[str, dict[str, Any]],
    report: dict[str, Any],
) -> list[str]:
    notes: list[str] = []
    for item in arguments:
        notes.extend(_strings(_object(argument_support.get(item)).get("evidence_summaries")))
    for item in innovations:
        notes.extend(_strings(_object(innovation_support.get(item)).get("evidence_summaries")))
    if not notes:
        notes.extend(_strings(report.get("consensus"))[:2])
    return _dedupe(notes)[:5]


def _coverage(
    items: list[str],
    support: dict[str, dict[str, Any]],
    sections: list[dict[str, Any]],
    kind: str,
) -> list[dict[str, Any]]:
    field = "linked_core_arguments" if kind == "argument" else "linked_innovation_points"
    key = "argument" if kind == "argument" else "innovation"
    result: list[dict[str, Any]] = []
    for item in items:
        matrix = _object(support.get(item))
        strength = _strength(matrix)
        covered = [section["section_id"] for section in sections if section["level"] == 1 and item in section[field]]
        claim_mode = "gap_or_discussion" if strength == "weak" else "supported_claim"
        treatment = "作为研究缺口、讨论或未来趋势谨慎展开。" if strength == "weak" else "作为章节论证的直接支撑展开。"
        result.append(
            {
                key: item,
                "support_strength": strength,
                "supporting_papers": _strings(matrix.get("supporting_papers")),
                "covered_by_sections": covered,
                "claim_mode": claim_mode,
                "treatment": treatment,
                "gap": str(matrix.get("gap") or ""),
            }
        )
    return result


def _matrix_by_key(value: Any, key: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in _list(value):
        if isinstance(item, dict) and str(item.get(key) or "").strip():
            result[str(item[key])] = item
    return result


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _strength(value: Any) -> str:
    strength = str(_object(value).get("support_strength") or "weak").lower()
    return strength if strength in {"strong", "moderate", "weak"} else "weak"


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _split_budget(total: int, count: int) -> list[int]:
    if count <= 0:
        return []
    base = total // count
    values = [base for _ in range(count)]
    values[-1] += total - sum(values)
    return values


def _role(title: str, level: int) -> str:
    if level == 2:
        return "展开上级章节中的具体论证要点。"
    if "摘要" in title:
        return "概括研究背景、核心论点、主要发现和贡献。"
    if "引言" in title:
        return "提出研究问题，界定研究范围，交代核心论点和创新点。"
    if "现状" in title or "脉络" in title:
        return "综合文献脉络，建立后续论证的知识基础。"
    if "缺口" in title or "趋势" in title or "挑战" in title:
        return "归纳未解决问题，谨慎展开弱支撑论点并提出未来方向。"
    if "结论" in title:
        return "回扣全文论点，总结贡献、局限和后续研究方向。"
    if "参考文献" in title:
        return "承载报告内部引用来源，不承担正文论证字数。"
    return "围绕任务书论点组织文献证据并形成主题化论证。"


def _transition(title: str) -> str:
    if "引言" in title:
        return "由问题提出转向文献脉络和概念边界。"
    if "现状" in title or "脉络" in title:
        return "由领域脉络转向关键主题、系统和指标的比较。"
    if "缺口" in title or "趋势" in title or "挑战" in title:
        return "由已有证据转向不足、挑战和未来研究方向。"
    if "结论" in title:
        return "收束全文并回应任务书中的核心论点与创新点。"
    return "为下一节提供概念、证据或比较基础。"


def _logic_graph(sections: list[dict[str, Any]]) -> list[dict[str, str]]:
    top = [section for section in sections if section["level"] == 1]
    return [
        {
            "from": top[index]["section_id"],
            "to": top[index + 1]["section_id"],
            "relation": f"{top[index]['title']} -> {top[index + 1]['title']}",
        }
        for index in range(len(top) - 1)
    ]


def _structure_rationale(paper_type: str) -> str:
    if paper_type == "survey":
        return "按照综述论文逻辑组织：先界定问题与领域脉络，再进行主题化比较，最后归纳研究缺口、趋势与结论。"
    if paper_type == "empirical":
        return "按照实证论文逻辑组织：从问题、相关工作和方法进入实验设计、结果讨论与结论。"
    if paper_type == "theoretical":
        return "按照理论论文逻辑组织：从相关研究进入理论框架、命题模型、分析讨论与结论。"
    return "按照任务书章节框架组织，并补充论点覆盖、文献支撑和字数预算。"


def _quality_flags(
    *,
    paper_type: str,
    sections: list[dict[str, Any]],
    argument_coverage: list[dict[str, Any]],
    innovation_coverage: list[dict[str, Any]],
    total: int,
    budgets: dict[str, int],
) -> list[str]:
    flags: list[str] = []
    if any(not item["covered_by_sections"] for item in argument_coverage):
        flags.append("存在未覆盖的核心论点。")
    if any(not item["covered_by_sections"] for item in innovation_coverage):
        flags.append("存在未覆盖的创新点。")
    if paper_type == "survey" and any(section["title"] in {"实验", "实验结果", "结果"} for section in sections):
        flags.append("综述型论文不应强行设置实验结果章节。")
    if sum(budget for key, budget in budgets.items() if key != "references") != total:
        flags.append("字数预算合计与总字数不一致。")
    weak_items = [item for item in argument_coverage + innovation_coverage if item["support_strength"] == "weak"]
    if weak_items:
        flags.append("部分论点或创新点文献支撑较弱，已按研究缺口/讨论/趋势处理。")
    return flags


def _render_markdown(outline: dict[str, Any]) -> str:
    lines: list[str] = [
        "# 论文详细大纲",
        "",
        "## 基本信息",
        "",
        f"- 主题：{outline['topic']}",
        f"- 论文类型：{outline['paper_type']}",
        f"- 总字数预算：{outline['total_word_budget']}",
        "",
        "## 结构设计说明",
        "",
        outline["structure_rationale"],
        "",
        "## 字数分配",
        "",
    ]
    for item in outline["word_budget_plan"]:
        lines.append(f"- {item['title']}：{item['word_budget']} 字")
    lines.extend(["", "## 详细大纲", ""])
    for section in outline["sections"]:
        if section["level"] == 1:
            lines.extend([f"## {section['title']}", ""])
        else:
            lines.extend([f"### {section['title']}", ""])
        lines.append(f"- 字数预算：{section['word_budget']} 字")
        lines.append(f"- 写作功能：{section['rhetorical_role']}")
        if section["core_points"]:
            lines.append(f"- 核心要点：{'；'.join(section['core_points'])}")
        if section["linked_core_arguments"]:
            lines.append(f"- 对应核心论点：{'；'.join(section['linked_core_arguments'])}")
        if section["linked_innovation_points"]:
            lines.append(f"- 对应创新点：{'；'.join(section['linked_innovation_points'])}")
        if section["supporting_papers"]:
            lines.append(f"- 支撑文献：{', '.join(section['supporting_papers'])}")
        if section["evidence_notes"]:
            lines.append(f"- 证据说明：{'；'.join(section['evidence_notes'])}")
        lines.append(f"- 逻辑衔接：{section['transition_out']}")
        lines.append("")
    lines.extend(["## 论点覆盖矩阵", ""])
    for item in outline["argument_coverage"]:
        lines.append(
            f"- {item['argument']}：{item['support_strength']}；章节 {', '.join(item['covered_by_sections']) or '未覆盖'}；{item['treatment']}；文献 {', '.join(item['supporting_papers']) or '无'}"
        )
    lines.extend(["", "## 创新点覆盖矩阵", ""])
    for item in outline["innovation_coverage"]:
        lines.append(
            f"- {item['innovation']}：{item['support_strength']}；章节 {', '.join(item['covered_by_sections']) or '未覆盖'}；{item['treatment']}；文献 {', '.join(item['supporting_papers']) or '无'}"
        )
    lines.extend(["", "## 质量检查", ""])
    if outline["quality_flags"]:
        for flag in outline["quality_flags"]:
            lines.append(f"- {flag}")
    else:
        lines.append("- 未发现结构性质量风险。")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
