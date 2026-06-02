"""Skill 2 · literature-review — entry script.

Usage::

    python run.py --state /path/to/state.json \
        [--refs <bib>] [--pdf-dir <dir>] [--text-file <txt>] \
        [--citation-style "GB/T 7714"]

Pipeline:
1. Load state, fetch writing_task.
2. Collect references from --refs / --pdf-dir / --text-file or, when none, from
   writing_task.references_seed.
3. Read Sub-agent intermediate paper claims from
   ``state.intermediate.literature_review.paper_claims``.
4. Read Sub-agent intermediate synthesis from
   ``state.intermediate.literature_review.synthesis``.
5. Citation formatter produces GB/T 7714-2015 + APA 7 strings.
6. Validate against LiteratureReport schema; write back to state.json; render
   Markdown to outputs/02-文献梳理报告.md.
"""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent.parent))  # `skills/` for _shared
sys.path.insert(0, str(_HERE))                # ensure local parsers/* resolve

from _shared.io import (  # noqa: E402
    append_history,
    load_state,
    resolve_workspace,
    save_state,
    write_output,
)
from _shared.schemas import LiteratureReport  # noqa: E402

from citation_formatter import format_apa, format_gb7714  # noqa: E402
from parsers.bibtex import parse_bibtex_file  # noqa: E402
from parsers.pdf import parse_pdf_dir, parse_pdf_file  # noqa: E402
from parsers.text import parse_text_file  # noqa: E402
from renderer import render_literature_report  # noqa: E402


REPO_ROOT = _HERE.parent.parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Skill 2 — literature-review")
    parser.add_argument("--state", required=True)
    parser.add_argument("--refs", action="append", default=[], help="path to .bib")
    parser.add_argument("--pdf-dir", default=None)
    parser.add_argument("--text-file", action="append", default=[])
    parser.add_argument("--citation-style", default=None)
    args = parser.parse_args()

    ws = resolve_workspace(args.state)
    state = load_state(ws)
    task = state.get("writing_task") or {}
    if not task:
        print(
            "[skill2] ERROR: state.writing_task missing. Run Skill 1 first.",
            file=sys.stderr,
        )
        return 1

    state["stage"] = "skill2_running"
    save_state(ws, state)

    started = time.perf_counter()
    try:
        papers = _collect_papers(args, task)
        if not papers:
            print(
                "[skill2] WARN: no papers found from --refs/--pdf-dir/--text-file or references_seed.",
                file=sys.stderr,
            )

        papers = _enrich_claims(papers, state)
        synthesis = _synthesize(state)
        papers = _merge_alignments(papers, synthesis.get("alignments", []))

        style = (
            args.citation_style
            or _style_from_task(task)
            or "GB/T 7714"
        )
        bibliography = {
            "gb7714": [format_gb7714(p) for p in papers],
            "apa": [format_apa(p) for p in papers],
        }

        report = {
            "keywords": _derive_keywords(task, papers),
            "papers": papers,
            "research_landscape": {
                "clusters": synthesis.get("clusters", []),
                "timeline_summary": synthesis.get("timeline_summary", ""),
            },
            "consensus": synthesis.get("consensus", []),
            "controversies": synthesis.get("controversies", []),
            "research_gaps": synthesis.get("research_gaps", []),
            "citation_style": style,
            "formatted_bibliography": bibliography,
        }
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc(file=sys.stderr)
        append_history(state, "literature-review", "error", message=str(exc))
        state["stage"] = "failed"
        save_state(ws, state)
        return 1

    try:
        validated = LiteratureReport.model_validate(report).model_dump()
    except Exception as exc:  # noqa: BLE001
        print(f"[skill2] WARN: validation failed ({exc}); writing raw payload.", file=sys.stderr)
        validated = report

    state["literature_report"] = validated
    state["stage"] = "skill2_done"
    duration_ms = int((time.perf_counter() - started) * 1000)
    append_history(
        state,
        "literature-review",
        "ok",
        message=(
            f"papers={len(validated.get('papers', []))} "
            f"clusters={len(validated.get('research_landscape', {}).get('clusters', []))} "
            f"gaps={len(validated.get('research_gaps', []))}"
        ),
        duration_ms=duration_ms,
    )
    save_state(ws, state)

    md = render_literature_report(
        validated, case_id=state.get("case_id", ""), topic=task.get("topic", "")
    )
    md_path = write_output(ws, "02-文献梳理报告.md", md)

    _emit_stdout_summary(validated, md_path, duration_ms)
    return 0


# --------------------------------------------------------------------------- #
# steps
# --------------------------------------------------------------------------- #


def _collect_papers(args: argparse.Namespace, task: dict[str, Any]) -> list[dict[str, Any]]:
    """Resolve every reference path and parse it into our uniform paper schema."""
    collected: list[dict[str, Any]] = []
    refs = list(args.refs) or []
    pdf_dir = args.pdf_dir
    text_files = list(args.text_file) or []

    seed = task.get("references_seed", []) or []
    if not (refs or pdf_dir or text_files) and seed:
        for s in seed:
            t = s.get("type")
            path = s.get("path")
            if not path:
                continue
            if t == "bibtex":
                refs.append(_resolve_path(path))
            elif t == "pdf":
                full = Path(_resolve_path(path))
                if full.is_dir():
                    pdf_dir = str(full)
                elif full.is_file():
                    try:
                        collected.append(parse_pdf_file(full))
                    except Exception as exc:  # noqa: BLE001
                        print(f"[skill2] WARN: cannot parse seed PDF {full}: {exc}", file=sys.stderr)
            elif t == "text":
                text_files.append(_resolve_path(path))

    for p in refs:
        full = _resolve_path(p)
        if not Path(full).exists():
            print(f"[skill2] WARN: bib file not found: {full}", file=sys.stderr)
            continue
        try:
            collected.extend(parse_bibtex_file(full))
        except Exception as exc:  # noqa: BLE001
            print(f"[skill2] WARN: bib parse failed {full}: {exc}", file=sys.stderr)

    if pdf_dir:
        collected.extend(parse_pdf_dir(_resolve_path(pdf_dir)))

    for tf in text_files:
        full = _resolve_path(tf)
        if not Path(full).exists():
            continue
        collected.extend(parse_text_file(full))

    # Dedupe by id (prefer richer record)
    by_id: dict[str, dict[str, Any]] = {}
    for paper in collected:
        pid = paper.get("id", "")
        if not pid:
            continue
        if pid not in by_id or len(paper.get("abstract") or "") > len(by_id[pid].get("abstract") or ""):
            by_id[pid] = paper
    return list(by_id.values())


def _resolve_path(p: str | Path) -> str:
    path = Path(p)
    if path.is_absolute():
        return str(path)
    # Relative paths in references_seed are anchored to the repo root.
    return str((REPO_ROOT / path).resolve())


def _enrich_claims(papers: list[dict[str, Any]], state: dict[str, Any]) -> list[dict[str, Any]]:
    raw_claims = _required_intermediate(
        state,
        "intermediate.literature_review.paper_claims",
        "Run a literature analysis Sub-agent before this Skill.",
    )
    claims = _normalize_claims(raw_claims)
    claims_by_id = {str(item.get("id") or item.get("paper_id")): item for item in claims if isinstance(item, dict)}
    out: list[dict[str, Any]] = []
    for p in papers:
        extracted = claims_by_id.get(str(p.get("id"))) or {}
        merged = dict(p)
        merged["key_claims"] = extracted.get("key_claims", []) or []
        merged["evidence_strength"] = extracted.get("evidence_strength", "weak")
        merged.setdefault("alignment_to_core", [])
        out.append(merged)
    return out


def _synthesize(state: dict[str, Any]) -> dict[str, Any]:
    synthesis = _required_intermediate(
        state,
        "intermediate.literature_review.synthesis",
        "Run a literature synthesis Sub-agent before this Skill.",
    )
    if not isinstance(synthesis, dict):
        raise ValueError("state.intermediate.literature_review.synthesis must be a JSON object.")
    return synthesis


def _required_intermediate(state: dict[str, Any], path: str, hint: str) -> Any:
    value = _get_path(state, path)
    if value is None:
        raise ValueError(f"{path} missing. {hint}")
    return value


def _get_path(root: dict[str, Any], dotted_path: str) -> Any:
    current: Any = root
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _normalize_claims(raw_claims: Any) -> list[dict[str, Any]]:
    if isinstance(raw_claims, list):
        return [item for item in raw_claims if isinstance(item, dict)]
    if isinstance(raw_claims, dict):
        for key in ("paper_claims", "papers", "claims"):
            value = raw_claims.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    raise ValueError(
        "state.intermediate.literature_review.paper_claims must be a list "
        "or an object containing paper_claims/papers/claims."
    )


def _merge_alignments(
    papers: list[dict[str, Any]], alignments: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_id: dict[str, list[dict[str, Any]]] = {}
    for a in alignments:
        pid = a.get("paper_id")
        if not pid:
            continue
        by_id.setdefault(pid, []).append(
            {
                "core_argument_index": a.get("core_argument_index", 0),
                "stance": a.get("stance", "neutral"),
                "note": a.get("note"),
            }
        )
    out: list[dict[str, Any]] = []
    for p in papers:
        rec = dict(p)
        rec["alignment_to_core"] = by_id.get(rec["id"], [])
        out.append(rec)
    return out


def _style_from_task(task: dict[str, Any]) -> str | None:
    tj = task.get("target_journal") or {}
    style = (tj.get("style_profile") or {}).get("citation_style")
    return style


def _derive_keywords(task: dict[str, Any], papers: list[dict[str, Any]]) -> list[str]:
    """Pick keywords from task.research_scope + paper venue tokens."""
    scope = task.get("research_scope") or {}
    keywords: list[str] = []
    if scope.get("domain"):
        keywords.extend([s.strip() for s in scope["domain"].split("·") if s.strip()])
    keywords.extend(scope.get("subtopics", []) or [])
    if not keywords:
        keywords = ["LLM Agent", "Skill", "学术写作辅助"]
    # Cap to first 10 unique
    seen: list[str] = []
    for k in keywords:
        if k not in seen:
            seen.append(k)
        if len(seen) >= 10:
            break
    return seen


def _emit_stdout_summary(report: dict[str, Any], md_path: Path, duration_ms: int) -> None:
    print("## Skill 2 · literature-review · 完成\n")
    print(f"- 文献条数：{len(report.get('papers', []))}")
    print(f"- 聚类数：{len(report.get('research_landscape', {}).get('clusters', []))}")
    print(f"- 共识：{len(report.get('consensus', []))} 条 / 争议：{len(report.get('controversies', []))} 条")
    print(f"- 研究缺口：{len(report.get('research_gaps', []))} 条")
    print(f"- 引用风格：{report.get('citation_style')}（同时输出 GB/T 7714 与 APA）")
    print(f"- Markdown 输出：`{md_path}`")
    print(f"- 用时：{duration_ms} ms")


if __name__ == "__main__":
    sys.exit(main())
