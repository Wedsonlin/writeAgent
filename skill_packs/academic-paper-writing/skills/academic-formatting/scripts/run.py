from __future__ import annotations

import argparse
import json
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
        markdown = _render_markdown(draft)
        if len(markdown) < 3000:
            raise ContractError("formatted markdown is too short for a paper artifact", ["formatted_draft.markdown"])
    except ContractError as exc:
        _write(args.output, {"artifact_type": "formatted_draft", "error": {"message": str(exc), "fields": exc.fields}})
        return 1

    markdown_path = str(Path(args.output).with_suffix(".md"))
    Path(markdown_path).write_text(markdown, encoding="utf-8")
    formatted = {
        "normalized_draft": draft,
        "markdown": markdown,
        "markdown_path": markdown_path,
        "issues": [],
    }
    _write(args.output, {"artifact_type": "formatted_draft", "formatted_draft": formatted})
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
    if isinstance(draft, dict) and "draft" in draft and isinstance(draft["draft"], dict):
        draft = draft["draft"]
    if not isinstance(draft, dict):
        raise ContractError("formatting input must include the full draft object", ["draft"])
    sections = draft.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ContractError("draft.sections is required", ["draft.sections"])
    return draft


def _render_markdown(draft: dict[str, Any]) -> str:
    lines: list[str] = []
    title = str(draft.get("title") or "未命名论文").strip()
    lines.extend([f"# {title}", ""])
    abstract = str(draft.get("abstract") or "").strip()
    if abstract:
        lines.extend(["## 摘要", "", abstract, ""])
    keywords = [str(item).strip() for item in draft.get("keywords", []) if str(item).strip()]
    if keywords:
        lines.extend(["**关键词**：" + "；".join(keywords), ""])
    for section in draft.get("sections", []):
        if not isinstance(section, dict):
            continue
        level = max(2, min(int(section.get("level") or 1) + 1, 6))
        title_text = str(section.get("title") or "").strip()
        content = str(section.get("content_markdown") or "").strip()
        if not title_text or not content:
            continue
        lines.extend([f"{'#' * level} {title_text}", "", content, ""])
    references = draft.get("references")
    if isinstance(references, list) and references:
        lines.extend(["## 参考文献", ""])
        for index, ref in enumerate(references, 1):
            text = _reference_text(ref)
            if text:
                lines.append(f"[{index}] {text}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _reference_text(ref: Any) -> str:
    if isinstance(ref, str):
        return ref.strip()
    if not isinstance(ref, dict):
        return ""
    for key in ("gb7714", "text", "citation", "title"):
        value = ref.get(key)
        if value:
            return str(value).strip()
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
