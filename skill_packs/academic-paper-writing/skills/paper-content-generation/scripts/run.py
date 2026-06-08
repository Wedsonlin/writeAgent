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

    def __str__(self) -> str:
        return self.message


def main() -> int:
    args = _parse()
    data = _load(args.input)
    try:
        draft = _extract_draft(data)
        _validate_draft(draft)
    except ContractError as exc:
        _write(args.output, {"artifact_type": "draft", "error": {"message": str(exc), "fields": exc.fields}})
        return 1

    _write(args.output, {"artifact_type": "draft", "draft": draft})
    return 0


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def _load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(path: str, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _extract_draft(data: dict[str, Any]) -> dict[str, Any]:
    draft = data.get("draft")
    if not isinstance(draft, dict):
        raise ContractError(
            "content-generation input must include a LLM-authored draft object, not artifact references only",
            ["draft"],
        )
    if _is_artifact_ref(draft):
        raise ContractError("draft must contain actual paper content instead of artifact_ref", ["draft.artifact_ref"])
    return {
        "title": str(draft.get("title") or data.get("title") or "未命名论文"),
        "abstract": str(draft.get("abstract") or "").strip(),
        "keywords": _string_list(draft.get("keywords")),
        "sections": [_normalize_section(section) for section in _list(draft.get("sections"))],
        "references": _list(draft.get("references")),
        "open_questions": _string_list(draft.get("open_questions")),
    }


def _normalize_section(section: Any) -> dict[str, Any]:
    if not isinstance(section, dict):
        raise ContractError("draft.sections[] must be objects", ["draft.sections"])
    content = str(section.get("content_markdown") or section.get("content") or "").strip()
    return {
        "id": str(section.get("id") or ""),
        "title": str(section.get("title") or ""),
        "level": int(section.get("level") or 1),
        "content_markdown": content,
        "citations_used": _string_list(section.get("citations_used")),
        "word_count": int(section.get("word_count") or _word_like_count(content)),
    }


def _validate_draft(draft: dict[str, Any]) -> None:
    missing: list[str] = []
    if not draft["title"].strip():
        missing.append("draft.title")
    if _word_like_count(draft["abstract"]) < 80:
        missing.append("draft.abstract")
    if len(draft["keywords"]) < 3:
        missing.append("draft.keywords")
    sections = draft["sections"]
    if len(sections) < 5:
        missing.append("draft.sections")
    for index, section in enumerate(sections):
        if not section["title"].strip():
            missing.append(f"draft.sections[{index}].title")
        if _word_like_count(section["content_markdown"]) < 120:
            missing.append(f"draft.sections[{index}].content_markdown")
        if "????" in section["content_markdown"] or "TODO" in section["content_markdown"].upper():
            missing.append(f"draft.sections[{index}].content_markdown.placeholder")
    total = sum(_word_like_count(section["content_markdown"]) for section in sections) + _word_like_count(draft["abstract"])
    if total < 2500:
        missing.append("draft.total_word_count")
    if missing:
        raise ContractError("draft content is incomplete or too short for a paper artifact", missing)


def _is_artifact_ref(value: Any) -> bool:
    return isinstance(value, dict) and set(value) == {"artifact_ref"}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
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
