"""Normalize SubAgent intermediate payloads into WritingTask-shaped dicts."""

from __future__ import annotations

import re
from typing import Any


_PAPER_TYPE_MAP = {
    "survey": "survey",
    "review": "survey",
    "综述": "survey",
    "综述论文": "survey",
    "empirical": "empirical",
    "实证": "empirical",
    "theoretical": "theoretical",
    "理论": "theoretical",
    "system": "system",
    "系统": "system",
    "case_study": "case_study",
    "案例": "case_study",
    "position": "position",
    "立场": "position",
}


def normalize_writing_task_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Coerce SubAgent output into fields expected by WritingTask validation."""
    result = dict(payload)
    prose = result.pop("raw_writing_task", None)
    if isinstance(prose, dict):
        nested = prose
        if isinstance(nested.get("raw_writing_task"), str):
            prose = nested["raw_writing_task"]
        for key, value in nested.items():
            if key != "raw_writing_task" and key not in result:
                result[key] = value

    if isinstance(prose, str) and prose.strip():
        parsed = _parse_markdown_task(prose)
        for key, value in parsed.items():
            if key == "chapter_framework" and result.get("chapter_framework"):
                continue
            if not result.get(key):
                result[key] = value

    paper_type = str(result.get("paper_type") or "")
    if paper_type and paper_type not in _PAPER_TYPE_MAP.values():
        mapped = _map_paper_type(paper_type)
        if mapped:
            result["paper_type"] = mapped

    if not result.get("core_arguments"):
        topic = str(result.get("topic") or "本论文主题")
        result["core_arguments"] = [f"围绕「{topic}」展开系统性论述。"]

    if not result.get("topic"):
        result["topic"] = "待定写作主题"

    if not result.get("paper_type"):
        result["paper_type"] = "survey"

    result.setdefault("language", "zh")
    result.setdefault("missing_info", [])
    result.setdefault("references_seed", [])
    result.setdefault("innovation_points", [])
    return result


def _parse_markdown_task(text: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    topic = _section_line(text, r"###\s*论文主题\s*\n+(.+?)(?=\n###|\Z)", re.DOTALL)
    if topic:
        parsed["topic"] = topic.splitlines()[0].strip()

    paper_type_raw = _section_line(text, r"###\s*论文类型\s*\n+(.+?)(?=\n###|\Z)", re.DOTALL)
    if paper_type_raw:
        mapped = _map_paper_type(paper_type_raw.splitlines()[0].strip())
        if mapped:
            parsed["paper_type"] = mapped

    core_block = _section_line(text, r"###\s*核心研究问题\s*\n+(.+?)(?=\n###|\Z)", re.DOTALL)
    if core_block:
        args = []
        for line in core_block.splitlines():
            line = line.strip()
            if not line:
                continue
            cleaned = re.sub(r"^\d+\.\s*", "", line)
            cleaned = re.sub(r"^\*\*(.+?)\*\*[:：]", r"\1：", cleaned)
            cleaned = cleaned.strip("- ").strip()
            if cleaned:
                args.append(cleaned)
        if args:
            parsed["core_arguments"] = args

    word_match = re.search(r"(\d{4,6})\s*[-~～]\s*(\d{4,6})\s*字", text)
    if word_match:
        parsed["word_limit"] = {"total": int(word_match.group(2))}
    else:
        single_word = re.search(r"约\s*(\d{4,6})\s*字", text)
        if single_word:
            parsed["word_limit"] = {"total": int(single_word.group(1))}

    chapters = _parse_chapter_framework(text)
    if chapters:
        parsed["chapter_framework"] = chapters

    domain_match = re.search(r"生成式\s*AI|AI\s*辅助", text, re.IGNORECASE)
    if domain_match:
        parsed["research_scope"] = {
            "domain": "生成式 AI 辅助学术写作",
            "subtopics": [],
            "boundary": "",
        }

    return parsed


def _parse_chapter_framework(text: str) -> list[dict[str, Any]]:
    chapters: list[dict[str, Any]] = []
    pattern = re.compile(
        r"####\s*第([一二三四五六七八九十\d]+)章\s*(.+?)\n(.*?)(?=\n####\s*第|\n###\s|\Z)",
        re.DOTALL,
    )
    cn_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    for match in pattern.finditer(text):
        index_raw, title, body = match.group(1), match.group(2).strip(), match.group(3)
        if index_raw.isdigit():
            chapter_id = index_raw
        else:
            chapter_id = str(cn_map.get(index_raw, len(chapters) + 1))
        key_points = []
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("- "):
                key_points.append(line[2:].strip())
        chapters.append(
            {
                "chapter_id": chapter_id,
                "title": title,
                "key_points": key_points,
                "word_budget": None,
            }
        )
    return chapters


def _map_paper_type(raw: str) -> str | None:
    lowered = raw.lower()
    for key, value in _PAPER_TYPE_MAP.items():
        if key in lowered or key in raw:
            return value
    return None


def _section_line(text: str, pattern: str, flags: int = 0) -> str | None:
    match = re.search(pattern, text, flags)
    if not match:
        return None
    return match.group(1).strip()
