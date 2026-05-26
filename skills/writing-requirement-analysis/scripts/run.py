"""Skill 1 · writing-requirement-analysis — entry script.

Usage::

    python run.py --state /path/to/state.json [--user-request "..."]

The script reads ``state.user_request``, asks the LLM (or the mock fallback) to
produce a structured ``writing_task`` JSON object, enriches it with a chapter
template and a journal-style profile, validates it against
``schemas/writing_task.schema.json`` (via the pydantic model in
``_shared.schemas``), then writes the result back to ``state.json`` and renders
a Markdown summary under ``outputs/01-论文写作任务书.md``.

Exit code 0 on success (even when missing_info is non-empty); 1 on hard errors.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent.parent))  # add `skills/` so `_shared` resolves

from _shared.io import (  # noqa: E402
    Workspace,
    append_history,
    load_state,
    now_iso,
    resolve_workspace,
    save_state,
    write_output,
)
from _shared.llm import is_mock_mode, structured_json  # noqa: E402
from _shared.schemas import WritingTask  # noqa: E402

from chapter_template import build_chapter_framework  # noqa: E402
from journal_match import match_journal_style  # noqa: E402
from prompts import build_messages, build_mock_payload  # noqa: E402
from renderer import render_task_book  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Skill 1 — writing-requirement-analysis"
    )
    parser.add_argument("--state", required=True, help="path to shared state.json")
    parser.add_argument(
        "--user-request",
        default=None,
        help="override state.user_request",
    )
    args = parser.parse_args()

    ws = resolve_workspace(args.state)
    state = load_state(ws)
    if args.user_request:
        state["user_request"] = args.user_request
    user_request = state.get("user_request", "").strip()
    if not user_request:
        print(
            "[skill1] ERROR: state.user_request is empty. "
            "Pass --user-request or fill state.json beforehand.",
            file=sys.stderr,
        )
        return 1

    state["stage"] = "skill1_running"
    save_state(ws, state)

    started = time.perf_counter()
    try:
        task_payload = _extract_writing_task(user_request)
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc(file=sys.stderr)
        append_history(state, "writing-requirement-analysis", "error", message=str(exc))
        state["stage"] = "failed"
        save_state(ws, state)
        return 1

    task_payload = _enrich(task_payload)

    try:
        validated = WritingTask.model_validate(task_payload).model_dump()
    except Exception as exc:  # noqa: BLE001
        print(f"[skill1] WARN: validation failed ({exc}); writing raw payload anyway.", file=sys.stderr)
        validated = task_payload

    state["writing_task"] = validated
    state["stage"] = "skill1_done"
    duration_ms = int((time.perf_counter() - started) * 1000)
    append_history(
        state,
        "writing-requirement-analysis",
        "ok",
        message=f"topic='{validated.get('topic', '')}' missing={len(validated.get('missing_info', []))}",
        duration_ms=duration_ms,
    )
    save_state(ws, state)

    md = render_task_book(validated, case_id=state.get("case_id", ""))
    md_path = write_output(ws, "01-论文写作任务书.md", md)

    _emit_stdout_summary(validated, md_path, duration_ms)
    return 0


# --------------------------------------------------------------------------- #
# core steps
# --------------------------------------------------------------------------- #


def _extract_writing_task(user_request: str) -> dict[str, Any]:
    """Ask the LLM (or mock) for a structured payload."""
    if is_mock_mode():
        return build_mock_payload(user_request)

    messages = build_messages(user_request)
    payload = structured_json(
        system_prompt=messages[0]["content"],
        user_prompt=messages[1]["content"],
        temperature=0.15,
    )
    if not isinstance(payload, dict):
        raise ValueError(f"LLM did not return a JSON object: {payload!r}")
    return payload


def _enrich(payload: dict[str, Any]) -> dict[str, Any]:
    """Post-process the LLM payload: style match + chapter template + missing-info sweep."""
    tj = payload.setdefault(
        "target_journal", {"name": "未指定", "level": "未指定"}
    )
    tj.setdefault("level", "未指定")
    tj["style_profile"] = match_journal_style(tj.get("name", ""), tj.get("level"))

    word_limit = payload.setdefault("word_limit", {})
    word_limit.setdefault("total", _default_word_total(payload.get("paper_type", "survey")))

    if not payload.get("chapter_framework"):
        payload["chapter_framework"] = build_chapter_framework(
            payload.get("paper_type", "survey"),
            int(word_limit.get("total", 8000)),
        )

    payload.setdefault("missing_info", [])
    _detect_missing(payload)
    payload.setdefault("references_seed", [])
    payload.setdefault("innovation_points", [])
    payload.setdefault("language", "zh")

    return payload


def _default_word_total(paper_type: str) -> int:
    return {
        "survey": 8000,
        "empirical": 6000,
        "theoretical": 8000,
        "system": 9000,
        "case_study": 5000,
        "position": 4000,
    }.get(paper_type, 6000)


def _detect_missing(payload: dict[str, Any]) -> None:
    """Add criticality-tagged missing_info entries for under-specified fields."""
    seen_fields = {m.get("field") for m in payload.get("missing_info", [])}

    def add(field: str, question: str, criticality: str, suggested_default: str | None = None) -> None:
        if field in seen_fields:
            return
        item: dict[str, Any] = {
            "field": field,
            "question": question,
            "criticality": criticality,
        }
        if suggested_default:
            item["suggested_default"] = suggested_default
        payload["missing_info"].append(item)
        seen_fields.add(field)

    tj = payload.get("target_journal", {})
    if not tj.get("name") or tj["name"] == "未指定":
        add(
            "target_journal.name",
            "目标期刊或会议是？（若不确定可填'未指定'）",
            "important",
            "计算机研究与发展",
        )

    if not payload.get("core_arguments"):
        add(
            "core_arguments",
            "论文要论证的核心论点有哪些？（至少 1 条）",
            "blocker",
            "请提供至少一句核心论点",
        )

    if not payload.get("innovation_points"):
        add(
            "innovation_points",
            "本文的创新点 / 主要贡献是什么？",
            "important",
            "由 Skill 2 文献综述结果反推",
        )


def _emit_stdout_summary(task: dict[str, Any], md_path: Path, duration_ms: int) -> None:
    print("## Skill 1 · writing-requirement-analysis · 完成\n")
    print(f"- 主题：{task.get('topic', '?')}")
    print(f"- 论文类型：{task.get('paper_type', '?')}")
    tj = task.get("target_journal", {})
    print(f"- 目标期刊：{tj.get('name', '?')}（{tj.get('level', '?')}）")
    print(f"- 总字数预算：{task.get('word_limit', {}).get('total', '?')}")
    missing = task.get("missing_info", [])
    if missing:
        print(f"- 缺失信息：{len(missing)} 项")
        for m in missing[:3]:
            print(f"  - {m.get('criticality', '?')} · {m.get('field', '?')}：{m.get('question', '?')}")
    print(f"- Markdown 输出：`{md_path}`")
    print(f"- 用时：{duration_ms} ms")


if __name__ == "__main__":
    sys.exit(main())
