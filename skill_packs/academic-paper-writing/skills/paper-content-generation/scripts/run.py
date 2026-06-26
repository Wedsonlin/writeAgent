from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ContractError(Exception):
    message: str
    fields: list[str]
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        return self.message


DEPTH_CHECK_KEYS = (
    "problem_framed",
    "mechanism_explained",
    "evidence_interpreted",
    "comparison_or_tradeoff",
    "limitation_or_boundary",
    "argument_return",
)

DEPTH_CUE_PATTERNS = {
    "mechanism_explained": re.compile(
        r"机制|通过|采用|实现|架构|系统|调度|缓存|分片|并行|运行时|服务|决定|协同|mechanism|architecture|scheduling|cache|parallel",
        re.IGNORECASE,
    ),
    "evidence_interpreted": re.compile(
        r"文献|研究|证据|表明|指出|显示|提出|证明|揭示|说明|evidence|study|paper|show|suggest",
        re.IGNORECASE,
    ),
    "comparison_or_tradeoff": re.compile(
        r"相比|相较|不同|差异|对比|比较|权衡|折中|一方面|另一方面|前者|后者|而不是|trade[- ]?off|compare|whereas",
        re.IGNORECASE,
    ),
    "limitation_or_boundary": re.compile(
        r"局限|不足|限制|边界|仍|尚|需要|难以|缺少|不能|不宜|待验证|开放问题|未来|limitation|boundary|open question",
        re.IGNORECASE,
    ),
    "argument_return": re.compile(
        r"因此|由此|这说明|这意味着|可见|综上|本文认为|本文主张|回到|支撑|回应|therefore|thus|this means",
        re.IGNORECASE,
    ),
}

CITATION_MARKER_RE = re.compile(r"\[(\d+(?:\s*[-–—,，]\s*\d+)*)\]")


def main() -> int:
    args = _parse()
    data = _load(args.input)
    output_path = Path(args.output)
    try:
        outline = _object_anchor(data, "outline")
        literature_report = _object_anchor(data, "literature_report")
        writing_task = _object_anchor(data, "writing_task")
        draft = _extract_draft(data, outline, literature_report)
        _validate_draft(draft, outline, literature_report, writing_task, data)
        markdown_path = output_path.with_suffix(".md")
        draft["quality_checks"] = _quality_checks(draft, outline)
        draft["draft_markdown"] = _render_markdown(draft)
        draft["draft_markdown_path"] = str(markdown_path)
        draft["quality_checks"]["markdown_sidecar_written"] = True
    except ContractError as exc:
        error: dict[str, Any] = {"message": str(exc), "fields": exc.fields}
        if exc.details:
            error["details"] = exc.details
        _write_json(output_path, {"artifact_type": "draft", "error": error})
        return 1

    _write_text(markdown_path, draft["draft_markdown"])
    _write_json(output_path, {"artifact_type": "draft", "draft": draft})
    return 0


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def _load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _object_anchor(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if isinstance(value, dict) and isinstance(value.get(key), dict):
        return value[key]
    if isinstance(value, dict):
        return value
    return {}


def _extract_draft(data: dict[str, Any], outline: dict[str, Any], literature_report: dict[str, Any]) -> dict[str, Any]:
    draft = data.get("draft")
    if not isinstance(draft, dict):
        raise ContractError(
            "content-generation input must include a LLM-authored draft object, not artifact references only",
            ["draft"],
        )
    if _is_artifact_ref(draft):
        raise ContractError("draft must contain actual paper content instead of artifact_ref", ["draft.artifact_ref"])

    references = _list(draft.get("references")) or _list(literature_report.get("references"))
    outline_budgets = _outline_budgets(outline)
    sections = [
        _normalize_section(section, outline_budgets)
        for section in _list(draft.get("sections"))
    ]
    return {
        "title": str(draft.get("title") or data.get("title") or "未命名论文").strip(),
        "abstract": str(draft.get("abstract") or "").strip(),
        "keywords": _string_list(draft.get("keywords")),
        "sections": sections,
        "references": references,
        "argument_trace": _list(draft.get("argument_trace")),
        "innovation_trace": _list(draft.get("innovation_trace")),
        "unsupported_claims": _string_list(draft.get("unsupported_claims")),
        "open_questions": _string_list(draft.get("open_questions")),
        "quality_checks": dict(draft.get("quality_checks") or {}),
    }


def _normalize_section(section: Any, outline_budgets: dict[str, int]) -> dict[str, Any]:
    if not isinstance(section, dict):
        raise ContractError("draft.sections[] must be objects", ["draft.sections"])
    content = str(section.get("content_markdown") or section.get("content") or "").strip()
    section_id = str(section.get("id") or section.get("section_id") or section.get("source_outline_section_id") or "").strip()
    source_outline_section_id = str(section.get("source_outline_section_id") or section_id).strip()
    target_word_count = int(section.get("target_word_count") or outline_budgets.get(source_outline_section_id) or 0)
    normalized = dict(section)
    normalized.update(
        {
            "id": section_id,
            "source_outline_section_id": source_outline_section_id,
            "title": str(section.get("title") or "").strip(),
            "level": int(section.get("level") or 1),
            "target_word_count": target_word_count,
            "content_markdown": content,
            "citations_used": _string_list(section.get("citations_used")),
            "linked_core_arguments": _string_list(section.get("linked_core_arguments")),
            "linked_innovation_points": _string_list(section.get("linked_innovation_points")),
            "evidence_used": _list(section.get("evidence_used")),
            "data_used": _list(section.get("data_used")),
            "transition_in": str(section.get("transition_in") or "").strip(),
            "transition_out": str(section.get("transition_out") or "").strip(),
            "support_status": str(section.get("support_status") or "unmapped").strip().lower(),
            "section_depth_checks": _normalize_depth_checks(section.get("section_depth_checks")),
            "word_count": int(section.get("word_count") or _word_like_count(content)),
        }
    )
    return normalized


def _validate_draft(
    draft: dict[str, Any],
    outline: dict[str, Any],
    literature_report: dict[str, Any],
    writing_task: dict[str, Any],
    raw_input: dict[str, Any],
) -> None:
    missing: list[str] = []
    if not draft["title"]:
        missing.append("draft.title")
    if _word_like_count(draft["abstract"]) < 80:
        missing.append("draft.abstract")
    if len(draft["keywords"]) < 3:
        missing.append("draft.keywords")
    if len(draft["sections"]) < 5:
        missing.append("draft.sections")
    if not draft["references"]:
        missing.append("draft.references")

    reference_index = _reference_index(draft["references"])
    outline_ids = _outline_ids(outline)
    support_lookup = _support_lookup(literature_report)
    citation_mismatches: list[dict[str, Any]] = []

    for index, section in enumerate(draft["sections"]):
        field = f"draft.sections[{index}]"
        if not section["title"]:
            missing.append(f"{field}.title")
        if _word_like_count(section["content_markdown"]) < 120:
            missing.append(f"{field}.content_markdown")
        if _has_placeholder(section["content_markdown"]):
            missing.append(f"{field}.content_markdown.placeholder")
        if _has_repetitive_template(section["content_markdown"]):
            missing.append(f"{field}.content_markdown.repetitive")
        if outline_ids and section["source_outline_section_id"] not in outline_ids:
            missing.append(f"{field}.source_outline_section_id")
        if section["support_status"] in {"strong", "moderate"} and (
            not section["citations_used"] or not section["evidence_used"]
        ):
            missing.append(f"{field}.support_status")
        if _uses_weak_support_as_strong(section, support_lookup):
            missing.append(f"{field}.support_status")
        _validate_section_citations(
            section,
            index,
            reference_index,
            len(draft["references"]),
            missing,
            citation_mismatches,
        )
        _validate_section_depth(section, index, missing)

    if _requires_empirical_data(writing_task, draft, raw_input):
        missing.append("research_data")

    if _word_like_count(draft["abstract"]) + sum(section["word_count"] for section in draft["sections"]) < 2500:
        missing.append("draft.total_word_count")

    if _expected_arguments(writing_task, outline) and not draft["argument_trace"]:
        missing.append("draft.argument_trace")
    if _expected_innovations(writing_task, outline) and not draft["innovation_trace"]:
        missing.append("draft.innovation_trace")

    if missing:
        details = {"citation_mismatches": citation_mismatches} if citation_mismatches else None
        raise ContractError(
            "draft content is incomplete, unsupported, or inconsistent with the outline/literature contract",
            sorted(set(missing)),
            details,
        )


def _validate_section_citations(
    section: dict[str, Any],
    section_index: int,
    reference_index: dict[str, int],
    reference_count: int,
    missing: list[str],
    citation_mismatches: list[dict[str, Any]],
) -> None:
    field = f"draft.sections[{section_index}]"
    markers = _citation_marker_numbers(section["content_markdown"])
    for marker in markers:
        if marker < 1 or marker > reference_count:
            missing.append(f"{field}.content_markdown.citation_marker")
    for citation_id in section["citations_used"]:
        expected_marker = _citation_id_to_marker(citation_id, reference_index, reference_count)
        if expected_marker is None:
            missing.append(f"{field}.citations_used")
            continue
        if expected_marker not in markers:
            missing.append(f"{field}.content_markdown.citation_marker")
            citation_mismatches.append(
                {
                    "section_index": section_index,
                    "section_title": section["title"],
                    "citation_id": citation_id,
                    "expected_marker": expected_marker,
                    "body_markers": sorted(markers),
                }
            )


def _validate_section_depth(section: dict[str, Any], section_index: int, missing: list[str]) -> None:
    field = f"draft.sections[{section_index}]"
    checks = section.get("section_depth_checks")
    if not isinstance(checks, dict) or any(not checks.get(key) for key in DEPTH_CHECK_KEYS):
        missing.append(f"{field}.section_depth_checks")
        return

    text = section["content_markdown"]
    if section["support_status"] in {"strong", "moderate"} and (
        not section["evidence_used"] or not _citation_marker_numbers(text)
    ):
        missing.append(f"{field}.section_depth_checks.evidence_interpreted")


def _citation_marker_numbers(text: str) -> set[int]:
    numbers: set[int] = set()
    for group in CITATION_MARKER_RE.findall(text):
        for part in re.split(r"[,，]", group):
            part = part.strip()
            if not part:
                continue
            range_match = re.fullmatch(r"(\d+)\s*[-–—]\s*(\d+)", part)
            if range_match:
                start = int(range_match.group(1))
                end = int(range_match.group(2))
                if start <= end:
                    numbers.update(range(start, end + 1))
                else:
                    numbers.update(range(end, start + 1))
                continue
            if part.isdigit():
                numbers.add(int(part))
    return numbers


def _citation_id_to_marker(
    citation_id: str,
    reference_index: dict[str, int],
    reference_count: int,
) -> int | None:
    citation_id = str(citation_id).strip()
    if citation_id.isdigit():
        marker = int(citation_id)
        if 1 <= marker <= reference_count:
            return marker
        return None
    if citation_id in reference_index:
        return reference_index[citation_id] + 1
    return None


def _normalize_depth_checks(value: Any) -> dict[str, bool]:
    if not isinstance(value, dict):
        return {}
    return {key: bool(value.get(key)) for key in DEPTH_CHECK_KEYS}


def _quality_checks(draft: dict[str, Any], outline: dict[str, Any]) -> dict[str, Any]:
    checks = dict(draft.get("quality_checks") or {})
    outline_ids = _outline_ids(outline)
    checks.update(
        {
            "outline_sections_covered": not outline_ids or all(
                section["source_outline_section_id"] in outline_ids for section in draft["sections"]
            ),
            "citations_valid": True,
            "argument_trace_present": bool(draft.get("argument_trace")),
            "innovation_trace_present": bool(draft.get("innovation_trace")),
            "unsupported_claims_recorded": "unsupported_claims" in draft,
            "open_questions_recorded": "open_questions" in draft,
            "section_depth_checked": all(
                all(section.get("section_depth_checks", {}).get(key) for key in DEPTH_CHECK_KEYS)
                for section in draft["sections"]
            ),
            "section_depth_cue_warnings": _section_depth_cue_warnings(draft["sections"]),
            "word_budget_warnings": _word_budget_warnings(draft["sections"]),
        }
    )
    return checks


def _section_depth_cue_warnings(sections: list[dict[str, Any]]) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    for index, section in enumerate(sections):
        text = section.get("content_markdown", "")
        for key, pattern in DEPTH_CUE_PATTERNS.items():
            if not pattern.search(text):
                warnings.append(
                    {
                        "section_index": str(index),
                        "section_id": str(section.get("source_outline_section_id") or section.get("id") or ""),
                        "cue": key,
                    }
                )
    return warnings


def _render_markdown(draft: dict[str, Any]) -> str:
    lines: list[str] = [f"# {draft['title']}", "", "## 摘要", "", draft["abstract"], ""]
    if draft["keywords"]:
        lines.extend([f"**关键词**：{'；'.join(draft['keywords'])}", ""])
    for section in draft["sections"]:
        level = min(max(int(section.get("level") or 1) + 1, 2), 6)
        lines.extend([f"{'#' * level} {section['title']}", "", section["content_markdown"], ""])
    if draft.get("open_questions"):
        lines.extend(["## 待确认问题", ""])
        lines.extend(f"- {item}" for item in draft["open_questions"])
        lines.append("")
    if draft.get("unsupported_claims"):
        lines.extend(["## 弱证据与未支撑声明", ""])
        lines.extend(f"- {item}" for item in draft["unsupported_claims"])
        lines.append("")
    lines.extend(["## 参考文献", ""])
    for index, reference in enumerate(draft["references"], start=1):
        lines.append(f"{index}. {_render_reference(reference)}")
    lines.append("")
    return "\n".join(lines)


def _render_reference(reference: Any) -> str:
    if isinstance(reference, dict):
        for key in ("gb7714", "apa", "formatted", "text"):
            if reference.get(key):
                return str(reference[key])
        title = str(reference.get("title") or reference.get("id") or "Untitled")
        year = str(reference.get("year") or "").strip()
        suffix = f", {year}" if year else ""
        return f"{title}{suffix}."
    return str(reference)


def _outline_budgets(outline: dict[str, Any]) -> dict[str, int]:
    budgets: dict[str, int] = {}
    for section in _list(outline.get("sections")):
        if not isinstance(section, dict):
            continue
        section_id = str(section.get("section_id") or section.get("id") or "").strip()
        if not section_id:
            continue
        try:
            budgets[section_id] = int(section.get("word_budget") or 0)
        except (TypeError, ValueError):
            budgets[section_id] = 0
    return budgets


def _outline_ids(outline: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for section in _list(outline.get("sections")):
        if isinstance(section, dict):
            section_id = str(section.get("section_id") or section.get("id") or "").strip()
            if section_id:
                ids.add(section_id)
    return ids


def _reference_index(references: list[Any]) -> dict[str, int]:
    index: dict[str, int] = {}
    for offset, reference in enumerate(references):
        ref_id = _reference_id(reference, offset)
        if ref_id:
            index[ref_id] = offset
    return index


def _reference_id(reference: Any, offset: int) -> str:
    if isinstance(reference, dict):
        for key in ("id", "paper_id", "citation_key", "key"):
            value = str(reference.get(key) or "").strip()
            if value:
                return value
    return str(offset + 1)


def _support_lookup(literature_report: dict[str, Any]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for key, target in (("argument_support_matrix", "argument"), ("innovation_support_matrix", "innovation")):
        for item in _list(literature_report.get(key)):
            if isinstance(item, dict):
                name = str(item.get(target) or "").strip()
                strength = str(item.get("support_strength") or "").strip().lower()
                if name and strength:
                    lookup[name] = strength
    return lookup


def _uses_weak_support_as_strong(section: dict[str, Any], support_lookup: dict[str, str]) -> bool:
    if section["support_status"] not in {"strong", "moderate"}:
        return False
    linked = section["linked_core_arguments"] + section["linked_innovation_points"]
    return any(support_lookup.get(item) == "weak" for item in linked)


def _requires_empirical_data(writing_task: dict[str, Any], draft: dict[str, Any], raw_input: dict[str, Any]) -> bool:
    paper_type = str(writing_task.get("paper_type") or raw_input.get("paper_type") or "").lower()
    if paper_type not in {"empirical", "experimental", "实证", "实验"}:
        return False
    research_data = _list(raw_input.get("research_data"))
    if research_data:
        return False
    result_pattern = re.compile(r"实验|结果|dataset|benchmark|accuracy|throughput|latency|吞吐|延迟", re.IGNORECASE)
    for section in draft["sections"]:
        if result_pattern.search(section["title"]) or result_pattern.search(section["content_markdown"]):
            if not section["data_used"]:
                return True
    return False


def _expected_arguments(writing_task: dict[str, Any], outline: dict[str, Any]) -> bool:
    return bool(_list(writing_task.get("core_arguments")) or _list(outline.get("argument_coverage")))


def _expected_innovations(writing_task: dict[str, Any], outline: dict[str, Any]) -> bool:
    return bool(_list(writing_task.get("innovation_points")) or _list(outline.get("innovation_coverage")))


def _word_budget_warnings(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for section in sections:
        target = int(section.get("target_word_count") or 0)
        if target <= 0:
            continue
        actual = int(section.get("word_count") or 0)
        if actual < target * 0.5 or actual > target * 1.5:
            warnings.append(
                {
                    "section_id": section.get("source_outline_section_id") or section.get("id"),
                    "target_word_count": target,
                    "actual_word_count": actual,
                }
            )
    return warnings


def _has_placeholder(text: str) -> bool:
    upper = text.upper()
    return any(token in upper for token in ("TODO", "TBD", "????")) or "待补充" in text or "待完善" in text


def _has_repetitive_template(text: str) -> bool:
    sentences = [
        sentence.strip()
        for sentence in re.split(r"[。！？.!?]\s*", text)
        if len(sentence.strip()) >= 12
    ]
    if not sentences:
        return False
    counts: dict[str, int] = {}
    for sentence in sentences:
        counts[sentence] = counts.get(sentence, 0) + 1
    if max(counts.values()) >= 6:
        return True
    generic_patterns = [
        "本节围绕",
        "该章节围绕",
        "展开讨论",
    ]
    generic_hits = sum(text.count(pattern) for pattern in generic_patterns)
    return generic_hits >= 8


def _is_artifact_ref(value: Any) -> bool:
    return isinstance(value, dict) and set(value) == {"artifact_ref"}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def _word_like_count(text: str) -> int:
    if not text:
        return 0
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_words = len(re.findall(r"[A-Za-z0-9_]+", text))
    return chinese_chars + latin_words


if __name__ == "__main__":
    raise SystemExit(main())
