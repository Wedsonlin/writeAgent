---
name: paper-outline
description: Use when paper_outline stage needs a Chinese detailed academic paper outline from a writing task and literature report, including section logic, word budgets, argument coverage, innovation coverage, and literature support.
---

# paper-outline

## Goal

Produce the `outline` artifact for workflow stage `paper_outline`. The outline is a structured argument plan, not a simple chapter list: it must convert the writing task and literature review into a section-by-section plan that downstream drafting can follow.

## Input Policy

Use Markdown as the semantic source and JSON as machine anchors:

- Prefer `task_book_markdown` / `task_book_markdown_path` for user-confirmed writing intent.
- Prefer `literature_report_markdown` / `literature_report_markdown_path` for the human-readable literature synthesis.
- Use stable `writing_task` anchors: `topic`, `paper_type`, `core_arguments`, `innovation_points`, `research_scope`, `word_limit`, `chapter_framework`, `task_book_sections.argument_evidence_matrix`.
- Use stable `literature_report` anchors: `research_landscape`, `argument_support_matrix`, `innovation_support_matrix`, `research_gaps`, `formatted_bibliography`.

If Markdown and JSON conflict, keep the Markdown framing and record the mismatch in `quality_flags`.

## Workflow

1. Identify paper type, topic, total word limit, core arguments, innovation points, and research scope.
2. Read the literature report for field context, support matrices, research gaps, and representative papers.
3. Select an outline pattern. Read `references/outline-patterns.md` when the paper type or structure is uncertain.
4. Map each argument and innovation to sections. Read `references/argument-section-mapping.md` when support coverage is incomplete or uneven.
5. Allocate word budgets. Read `references/word-budget-rubric.md` when `word_limit.by_chapter` is null.
6. Check the outline against `references/outline-quality-rubric.md`.
7. Run `scripts/run.py` with a JSON input containing the upstream content and write a JSON + Markdown output.

## Output Contract

The script writes:

- `artifact_type`: `outline`
- `outline`: machine-readable detailed outline
- `outline_markdown`: human-readable Markdown outline
- `outline_markdown_path`: path to the Markdown file

`outline.sections[]` must include first-level and second-level sections. Each major body section must state its rhetorical role, core points, linked core arguments, linked innovation points, supporting papers, evidence notes, and transition notes.

## Quality Rules

- Do not merely restate `chapter_framework`.
- Do not force empirical “实验/结果” sections for survey papers unless the task explicitly requires empirical evaluation.
- Every `core_arguments[]` and `innovation_points[]` item must appear in coverage matrices.
- Weakly supported arguments or innovations must be framed as research gaps, limitations, discussion points, or future trends.
- The total positive word budget must match `writing_task.word_limit.total` when provided.
- Write the outline in Chinese except for English-native terms, article titles, names, systems, models, citation keys, URLs, and DOIs.
