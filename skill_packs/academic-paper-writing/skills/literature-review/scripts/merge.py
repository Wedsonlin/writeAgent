from __future__ import annotations

from typing import Any

from validate import validate_report


def build_literature_report(
    data: dict[str, Any],
    papers: list[dict[str, Any]],
    bibliography: dict[str, list[str]],
) -> dict[str, Any]:
    task = data.get("writing_task", {})
    source_map = {item.get("paper_id"): item for item in data.get("source_map", []) if isinstance(item, dict)}
    merged_papers = [_merge_paper(paper, source_map.get(paper.get("id"))) for paper in papers]
    landscape = data.get("landscape", {})

    report = {
        "keywords": _keywords(task, landscape),
        "papers": merged_papers,
        "research_landscape": {
            "clusters": landscape.get("clusters", []),
            "timeline_summary": landscape.get("timeline_summary", ""),
        },
        "consensus": landscape.get("consensus", []),
        "controversies": landscape.get("controversies", []),
        "research_gaps": landscape.get("research_gaps", []),
        "citation_style": data.get("citation_style") or _citation_style(task),
        "formatted_bibliography": bibliography,
    }

    validate_report(report, len(task.get("core_arguments", [])))
    return report


def _merge_paper(paper: dict[str, Any], source: dict[str, Any] | None) -> dict[str, Any]:
    if source is None:
        paper_id = paper.get("id") or "<unknown>"
        raise ValueError(f"source_map is missing required evidence for paper {paper_id}")
    key_claims = _string_list(source.get("key_claims"))
    if not key_claims:
        paper_id = paper.get("id") or "<unknown>"
        raise ValueError(f"source_map[{paper_id}].key_claims is required")
    return {
        "id": paper.get("id"),
        "type": paper.get("type"),
        "title": paper.get("title"),
        "authors": paper.get("authors", []),
        "year": paper.get("year"),
        "venue": paper.get("venue", ""),
        "doi": paper.get("doi"),
        "url": paper.get("url"),
        "abstract": paper.get("abstract", ""),
        "key_claims": key_claims,
        "evidence_strength": source.get("evidence_strength") or "weak",
        "alignment_to_core": source.get("alignment_to_core") or [],
        "source_kind": paper.get("source_kind", "bibtex"),
        "limitations": source.get("limitations", []),
        "provenance": source.get("provenance", {}),
    }


def _keywords(task: dict[str, Any], landscape: dict[str, Any]) -> list[str]:
    values: list[str] = []
    values.extend(_string_list(landscape.get("keywords")))
    scope = task.get("research_scope") if isinstance(task.get("research_scope"), dict) else {}
    domain = scope.get("domain")
    if domain:
        values.extend([item.strip() for item in str(domain).replace("·", ",").split(",") if item.strip()])
    values.extend(_string_list(scope.get("subtopics")))
    return _dedupe(values)


def _citation_style(task: dict[str, Any]) -> str:
    journal = task.get("target_journal") if isinstance(task.get("target_journal"), dict) else {}
    profile = journal.get("style_profile") if isinstance(journal.get("style_profile"), dict) else {}
    return str(profile.get("citation_style") or "GB/T 7714")


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
