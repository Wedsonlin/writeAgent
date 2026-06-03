"""Skill 3 · paper-outline — deterministic outline builder from writing_task."""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent.parent))

from _shared.io import append_history, load_state, resolve_workspace, save_state, write_output  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Skill 3 — paper-outline")
    parser.add_argument("--state", required=True, help="path to shared state.json")
    args = parser.parse_args()

    ws = resolve_workspace(args.state)
    state = load_state(ws)
    task = state.get("writing_task") or {}
    if not task:
        print("[skill3] ERROR: state.writing_task missing. Run Skill 1 first.", file=sys.stderr)
        return 1

    state["stage"] = "skill3_running"
    save_state(ws, state)
    started = time.perf_counter()

    try:
        outline = _build_outline(task)
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc(file=sys.stderr)
        append_history(state, "paper-outline", "error", message=str(exc))
        state["stage"] = "failed"
        save_state(ws, state)
        return 1

    state["outline"] = outline
    state["stage"] = "skill3_done"
    duration_ms = int((time.perf_counter() - started) * 1000)
    append_history(
        state,
        "paper-outline",
        "ok",
        message=f"sections={len(outline.get('sections', []))}",
        duration_ms=duration_ms,
    )
    save_state(ws, state)

    md = _render_outline_md(outline, task)
    md_path = write_output(ws, "03-论文详细大纲.md", md)
    print("## Skill 3 · paper-outline · 完成\n")
    print(f"- 章节数：{len(outline.get('sections', []))}")
    print(f"- 总字数预算：{outline.get('total_word_budget')}")
    print(f"- Markdown 输出：`{md_path}`")
    print(f"- 用时：{duration_ms} ms")
    return 0


def _build_outline(task: dict[str, Any]) -> dict[str, Any]:
    total = int((task.get("word_limit") or {}).get("total") or 8000)
    framework = list(task.get("chapter_framework") or [])
    if not framework:
        framework = [
            {"chapter_id": "1", "title": "引言", "key_points": ["研究背景"], "word_budget": max(total // 8, 500)},
            {"chapter_id": "2", "title": "相关工作", "key_points": ["文献回顾"], "word_budget": max(total // 4, 800)},
            {"chapter_id": "3", "title": "主体分析", "key_points": ["核心内容"], "word_budget": max(total // 2, 1200)},
            {"chapter_id": "4", "title": "结论", "key_points": ["总结与展望"], "word_budget": max(total // 8, 500)},
        ]

    sections: list[dict[str, Any]] = []
    for item in framework:
        chapter_id = str(item.get("chapter_id") or item.get("id") or len(sections) + 1)
        word_budget = item.get("word_budget")
        if word_budget is None:
            word_budget = max(total // max(len(framework), 1), 400)
        sections.append(
            {
                "id": chapter_id,
                "title": str(item.get("title") or f"第{chapter_id}章"),
                "level": 1,
                "parent_id": None,
                "key_points": list(item.get("key_points") or []),
                "transition_note": "",
                "word_budget": int(word_budget),
                "supporting_papers": [],
            }
        )

    budget_sum = sum(int(section.get("word_budget") or 0) for section in sections)
    if budget_sum <= 0:
        per = max(total // max(len(sections), 1), 400)
        for section in sections:
            section["word_budget"] = per
        budget_sum = per * len(sections)

    return {"total_word_budget": budget_sum, "sections": sections}


def _render_outline_md(outline: dict[str, Any], task: dict[str, Any]) -> str:
    lines = [
        f"# 论文详细大纲 · {task.get('topic', '（待定）')}",
        "",
        f"- 论文类型：{task.get('paper_type', '?')}",
        f"- 总字数预算：{outline.get('total_word_budget', '?')}",
        "",
        "## 章节结构",
        "",
    ]
    for section in outline.get("sections", []):
        points = "；".join(section.get("key_points") or []) or "（待补充）"
        lines.append(
            f"### {section.get('id', '?')} {section.get('title', '（无标题）')} "
            f"（约 {section.get('word_budget', '?')} 字）"
        )
        lines.append(f"- 要点：{points}")
        if section.get("transition_note"):
            lines.append(f"- 衔接：{section['transition_note']}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
