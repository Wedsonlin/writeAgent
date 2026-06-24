from __future__ import annotations

import re
from typing import Any

from validate import validate_report


def build_literature_report(
    data: dict[str, Any],
    papers: list[dict[str, Any]],
    bibliography: dict[str, list[str]],
) -> dict[str, Any]:
    task = data.get("writing_task", {})
    source_map = {item.get("paper_id"): item for item in data.get("source_map", []) if isinstance(item, dict)}
    reading_cards = [item for item in data.get("paper_reading_cards", []) if isinstance(item, dict)]
    card_map = {item.get("paper_id"): item for item in reading_cards if item.get("paper_id")}
    merged_papers: list[dict[str, Any]] = []
    unmapped_papers: list[str] = []
    for paper in papers:
        source = source_map.get(paper.get("id"))
        card = card_map.get(paper.get("id"))
        merged = _merge_paper(paper, source, card)
        merged_papers.append(merged)
        if (source is None and card is None) or not merged.get("key_claims"):
            unmapped_papers.append(str(paper.get("id") or "<unknown>"))
    landscape = data.get("landscape", {})
    localized_landscape = _localized_landscape(landscape)
    argument_support_matrix = _support_matrix(
        provided=data.get("argument_support_matrix"),
        cards=reading_cards,
        targets=_string_list(task.get("core_arguments")),
        relation_key="relevance_to_arguments",
        index_key="core_argument_index",
        target_key="argument",
    )
    innovation_support_matrix = _support_matrix(
        provided=data.get("innovation_support_matrix"),
        cards=reading_cards,
        targets=_string_list(task.get("innovation_points")),
        relation_key="relevance_to_innovations",
        index_key="innovation_index",
        target_key="innovation",
    )

    report = {
        "keywords": _keywords(data, task, landscape),
        "papers": merged_papers,
        "paper_reading_cards": reading_cards,
        "task_alignment": _task_alignment(task),
        "argument_support_matrix": argument_support_matrix,
        "innovation_support_matrix": innovation_support_matrix,
        "research_landscape": {
            "clusters": localized_landscape.get("clusters", []),
            "timeline_summary": localized_landscape.get("timeline_summary", ""),
        },
        "consensus": localized_landscape.get("consensus", []),
        "controversies": localized_landscape.get("controversies", []),
        "research_gaps": localized_landscape.get("research_gaps", []),
        "supplement_search_summary": _supplement_search_summary(data, argument_support_matrix, innovation_support_matrix),
        "citation_style": data.get("citation_style") or _citation_style(task),
        "formatted_bibliography": bibliography,
    }
    if unmapped_papers:
        report["unmapped_papers"] = unmapped_papers
    report["report_sections"] = _report_sections(report)

    validate_report(report, len(task.get("core_arguments", [])))
    return report


def _merge_paper(paper: dict[str, Any], source: dict[str, Any] | None, card: dict[str, Any] | None) -> dict[str, Any]:
    if source is None:
        source = {
            "key_claims": [],
            "evidence_strength": "weak",
            "alignment_to_core": [],
            "limitations": [],
            "provenance": {"status": "unmapped"},
        }
    key_claims = _card_claims(card) if card is not None else _string_list(_localized_value(source, "key_claims"))
    provenance = source.get("provenance", {})
    if not isinstance(provenance, dict):
        provenance = {"source": provenance}
    if card is not None:
        provenance = {
            **provenance,
            "status": "paper_reading_card",
            "reading_status": card.get("reading_status"),
            "source_urls": _string_list(card.get("source_urls")),
            "source_artifact_ids": _string_list(card.get("source_artifact_ids")),
        }
    if not key_claims and "status" not in provenance:
        provenance = {**provenance, "status": "missing_key_claims"}
    evidence_strength = _evidence_strength(source, card, provenance)
    return {
        "id": paper.get("id"),
        "type": paper.get("type"),
        "title": paper.get("title"),
        "authors": paper.get("authors", []),
        "year": paper.get("year"),
        "venue": paper.get("venue", ""),
        "doi": paper.get("doi"),
        "url": paper.get("url"),
        "abstract": _paper_abstract(paper, source, card),
        "research_problem": card.get("research_problem_zh") if card is not None else source.get("research_question"),
        "core_method": card.get("method_zh") if card is not None else source.get("core_method"),
        "evidence": _string_list(card.get("evidence_zh")) if card is not None else [],
        "key_claims": key_claims,
        "evidence_strength": evidence_strength,
        "alignment_to_core": _alignment_to_core(source, card),
        "alignment_to_innovations": card.get("relevance_to_innovations", []) if card is not None else [],
        "source_kind": paper.get("source_kind", "bibtex"),
        "limitations": _card_limitations(card) if card is not None else (_localized_value(source, "limitations") or []),
        "provenance": provenance,
    }


def _card_claims(card: dict[str, Any] | None) -> list[str]:
    if card is None:
        return []
    return _string_list(card.get("main_claims_zh") or card.get("main_claims"))


def _card_limitations(card: dict[str, Any] | None) -> list[Any]:
    if card is None:
        return []
    return card.get("limitations_zh") or card.get("limitations") or []


def _paper_abstract(paper: dict[str, Any], source: dict[str, Any], card: dict[str, Any] | None) -> str:
    source_abstract = _localized_value(source, "abstract")
    if source_abstract:
        return source_abstract
    if card is not None:
        card_abstract = card.get("abstract_zh") or card.get("abstract")
        if card_abstract:
            return str(card_abstract)
        claims = _card_claims(card)
        if claims:
            return claims[0]
    return paper.get("abstract", "")


def _alignment_to_core(source: dict[str, Any], card: dict[str, Any] | None) -> list[dict[str, Any]]:
    if card is None:
        return source.get("alignment_to_core") or []
    alignments: list[dict[str, Any]] = []
    for item in card.get("relevance_to_arguments", []) or []:
        if not isinstance(item, dict):
            continue
        alignments.append(
            {
                "core_argument_index": item.get("core_argument_index"),
                "stance": item.get("stance"),
                "support_strength": item.get("support_strength"),
                "note": item.get("evidence_summary_zh") or item.get("note") or "",
            }
        )
    return alignments


def _evidence_strength(source: dict[str, Any], card: dict[str, Any] | None, provenance: dict[str, Any]) -> str:
    if card is not None:
        strengths = [
            str(item.get("support_strength"))
            for item in list(card.get("relevance_to_arguments") or []) + list(card.get("relevance_to_innovations") or [])
            if isinstance(item, dict) and item.get("support_strength")
        ]
        strength = _max_strength(strengths) or str(source.get("evidence_strength") or "moderate")
        if not _has_grounding(card):
            provenance["status"] = "ungrounded_paper_reading_card"
            return "weak"
        return strength if strength in {"strong", "moderate", "weak"} else "weak"

    strength = str(source.get("evidence_strength") or "weak")
    if strength in {"strong", "moderate"} and not _has_grounding(source):
        provenance["status"] = "ungrounded_source_map"
        return "weak"
    return strength if strength in {"strong", "moderate", "weak"} else "weak"


def _has_grounding(item: dict[str, Any]) -> bool:
    if _string_list(item.get("source_artifact_ids")) and _string_list(item.get("source_urls")):
        return True
    provenance = item.get("provenance") if isinstance(item.get("provenance"), dict) else {}
    return bool(_string_list(provenance.get("source_artifact_ids")) and _string_list(provenance.get("source_urls")))


def _localized_landscape(landscape: dict[str, Any]) -> dict[str, Any]:
    return {
        "clusters": [_localized_cluster(cluster) for cluster in landscape.get("clusters", []) if isinstance(cluster, dict)],
        "timeline_summary": _localized_value(landscape, "timeline_summary") or "",
        "consensus": _string_list(_localized_value(landscape, "consensus")),
        "controversies": _string_list(_localized_value(landscape, "controversies")),
        "research_gaps": _string_list(_localized_value(landscape, "research_gaps")),
    }


def _localized_cluster(cluster: dict[str, Any]) -> dict[str, Any]:
    localized = {
        key: value
        for key, value in cluster.items()
        if not key.endswith("_zh") and not key.endswith("_cn") and not key.startswith("localized_")
    }
    localized["name"] = _localized_value(cluster, "name") or cluster.get("name", "")
    localized["summary"] = _localized_value(cluster, "summary") or cluster.get("summary", "")
    return localized


def _localized_value(container: dict[str, Any], key: str) -> Any:
    for candidate in (f"{key}_zh", f"{key}_cn", f"localized_{key}"):
        value = container.get(candidate)
        if value:
            return value
    return container.get(key)


def _task_alignment(task: dict[str, Any]) -> dict[str, Any]:
    sections = task.get("task_book_sections") if isinstance(task.get("task_book_sections"), dict) else {}
    return {
        "topic": task.get("topic", ""),
        "core_arguments": _string_list(task.get("core_arguments")),
        "innovation_points": _string_list(task.get("innovation_points")),
        "research_scope": task.get("research_scope") if isinstance(task.get("research_scope"), dict) else {},
        "argument_evidence_matrix": sections.get("argument_evidence_matrix", []),
    }


def _support_matrix(
    *,
    provided: Any,
    cards: list[dict[str, Any]],
    targets: list[str],
    relation_key: str,
    index_key: str,
    target_key: str,
) -> list[dict[str, Any]]:
    if isinstance(provided, list) and provided:
        return [item for item in provided if isinstance(item, dict)]
    matrix: list[dict[str, Any]] = []
    for index, target in enumerate(targets):
        supporting_papers: list[str] = []
        evidence_summaries: list[str] = []
        strengths: list[str] = []
        for card in cards:
            paper_id = str(card.get("paper_id") or "")
            if not paper_id:
                continue
            for relation in card.get(relation_key, []) or []:
                if not isinstance(relation, dict) or relation.get(index_key) != index:
                    continue
                stance = str(relation.get("stance") or "")
                strength = str(relation.get("support_strength") or "weak")
                if stance in {"supports", "extends"} and strength in {"strong", "moderate"} and _has_grounding(card):
                    supporting_papers.append(paper_id)
                    strengths.append(strength)
                summary = relation.get("evidence_summary_zh") or relation.get("note")
                if summary:
                    evidence_summaries.append(str(summary))
        supporting_papers = _dedupe(supporting_papers)
        strength = _max_strength(strengths) or "weak"
        matrix.append(
            {
                "index": index,
                target_key: target,
                "supporting_papers": supporting_papers,
                "support_strength": strength,
                "evidence_summaries": _dedupe(evidence_summaries),
                "gap": "" if supporting_papers else "缺少直接支撑文献，需要补充检索。",
            }
        )
    return matrix


def _supplement_search_summary(
    data: dict[str, Any],
    argument_support_matrix: list[dict[str, Any]],
    innovation_support_matrix: list[dict[str, Any]],
) -> dict[str, Any]:
    provided = data.get("supplement_search_summary")
    if isinstance(provided, dict):
        return provided
    uncovered_arguments = [item.get("argument") for item in argument_support_matrix if not item.get("supporting_papers")]
    uncovered_innovations = [item.get("innovation") for item in innovation_support_matrix if not item.get("supporting_papers")]
    needs_search = bool(uncovered_arguments or uncovered_innovations)
    return {
        "status": "needed" if needs_search else "not_required",
        "uncovered_arguments": [str(item) for item in uncovered_arguments if item],
        "uncovered_innovations": [str(item) for item in uncovered_innovations if item],
        "summary": "存在未覆盖论点或创新点，需要补充检索。" if needs_search else "现有精读文献已覆盖任务书中的核心论点与创新点。",
    }


def _max_strength(values: list[str]) -> str | None:
    order = {"weak": 0, "moderate": 1, "strong": 2}
    ranked = [value for value in values if value in order]
    if not ranked:
        return None
    return max(ranked, key=lambda item: order[item])


def _keywords(data: dict[str, Any], task: dict[str, Any], landscape: dict[str, Any]) -> list[str]:
    values: list[str] = []
    values.extend(_string_list(data.get("research_keywords")))
    values.extend(_keywords_from_task_book(data.get("task_book_markdown")))
    values.extend(_string_list(landscape.get("keywords")))
    scope = task.get("research_scope") if isinstance(task.get("research_scope"), dict) else {}
    domain = scope.get("domain")
    if domain:
        values.extend([item.strip() for item in str(domain).replace("·", ",").split(",") if item.strip()])
    values.extend(_string_list(scope.get("subtopics")))
    return _dedupe(values)


def _keywords_from_task_book(markdown: Any) -> list[str]:
    text = str(markdown or "")
    values: list[str] = []
    for line in text.splitlines():
        if not re.search(r"(研究方向)?关键词", line):
            continue
        parts = re.split(r"[:：]", line, maxsplit=1)
        if len(parts) != 2:
            continue
        values.extend(_split_keywords(parts[1]))
    return values


def _split_keywords(text: str) -> list[str]:
    return [item.strip(" \t\r\n`*_-.") for item in re.split(r"[;；,，、/|]+", text) if item.strip(" \t\r\n`*_-.")]


def _citation_style(task: dict[str, Any]) -> str:
    journal = task.get("target_journal") if isinstance(task.get("target_journal"), dict) else {}
    profile = journal.get("style_profile") if isinstance(journal.get("style_profile"), dict) else {}
    return str(profile.get("citation_style") or "GB/T 7714")


def _report_sections(report: dict[str, Any]) -> dict[str, Any]:
    landscape = report.get("research_landscape", {})
    research_status = _string_list(report.get("consensus"))
    if report.get("controversies"):
        research_status.extend(f"争议：{item}" for item in _string_list(report.get("controversies")))
    if not research_status:
        research_status = ["现有文献围绕关键词与主题簇形成初步研究基础。"]
    return {
        "task_alignment": report.get("task_alignment", {}),
        "research_status": research_status,
        "field_context": {
            "clusters": landscape.get("clusters", []),
            "timeline_summary": landscape.get("timeline_summary", ""),
        },
        "core_literature_viewpoints": [_paper_viewpoint(paper) for paper in report.get("papers", [])],
        "argument_support_matrix": list(report.get("argument_support_matrix", [])),
        "innovation_support_matrix": list(report.get("innovation_support_matrix", [])),
        "research_gaps": _string_list(report.get("research_gaps")),
        "supplement_search_summary": report.get("supplement_search_summary", {}),
        "references": {
            "gb7714": list(report.get("formatted_bibliography", {}).get("gb7714", [])),
            "apa": list(report.get("formatted_bibliography", {}).get("apa", [])),
        },
    }


def _paper_viewpoint(paper: dict[str, Any]) -> dict[str, Any]:
    return {
        "paper_id": paper.get("id"),
        "title": paper.get("title"),
        "year": paper.get("year"),
        "key_claims": paper.get("key_claims", []),
        "evidence_strength": paper.get("evidence_strength"),
    }


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None and str(item)]
    return [str(value)]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
