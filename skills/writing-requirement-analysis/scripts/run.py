"""Skill 1 · writing-requirement-analysis — entry script.

Usage::

    python run.py --state /path/to/state.json [--user-request "..."]

The script reads ``state.intermediate.requirement.raw_writing_task`` produced by
a dynamic Sub-agent, enriches it with a chapter template and a journal-style
profile, validates it against
``schemas/writing_task.schema.json`` (via the pydantic model in
``_shared.schemas``), then writes the result back to ``state.json`` and renders
a Markdown summary under ``outputs/01-论文写作任务书.md``.

Exit code 0 on success (even when missing_info is non-empty); 1 on hard errors.
"""

from __future__ import annotations

import argparse
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
from _shared.schemas import WritingTask  # noqa: E402

from chapter_template import build_chapter_framework  # noqa: E402
from journal_match import match_journal_style  # noqa: E402
from normalize import normalize_writing_task_payload  # noqa: E402
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
        raw_payload = _extract_writing_task(state)
        task_payload = normalize_writing_task_payload(raw_payload)
        # #region agent log
        _debug_log(
            "H-C",
            "skills/writing-requirement-analysis/scripts/run.py:main",
            "normalized writing task payload",
            {
                "raw_keys": sorted(raw_payload.keys()),
                "topic": task_payload.get("topic"),
                "paper_type": task_payload.get("paper_type"),
                "core_arguments_len": len(task_payload.get("core_arguments") or []),
                "chapter_framework_len": len(task_payload.get("chapter_framework") or []),
            },
        )
        # #endregion
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


def _extract_writing_task(state: dict[str, Any]) -> dict[str, Any]:
    """Read the Sub-agent generated structured payload from state.intermediate."""
    payload = _get_path(state, "intermediate.requirement.raw_writing_task")
    if payload is None:
        raise ValueError(
            "state.intermediate.requirement.raw_writing_task missing. "
            "Run a requirement analysis Sub-agent before this Skill."
        )
    if not isinstance(payload, dict):
        raise ValueError(
            "state.intermediate.requirement.raw_writing_task must be a JSON object."
        )
    return payload


def _get_path(root: dict[str, Any], dotted_path: str) -> Any:
    current: Any = root
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


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


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict[str, Any]) -> None:
    import json
    import time

    payload = {
        "sessionId": "755fc4",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    log_path = _HERE.parent.parent.parent / "debug-755fc4.log"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


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
