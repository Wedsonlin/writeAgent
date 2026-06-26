---
name: paper-content-generation
description: Use when content_generation stage needs to turn an outline and literature report into a Chinese academic draft with citations, evidence traces, and section-level prose.
---

# paper-content-generation

## Goal

Produce the `draft` artifact for workflow stage `content_generation`. The draft is evidence-grounded paper prose, not an expanded outline: every substantive section must follow the outline, cite supported literature, and record how it uses core arguments, innovation points, evidence, and data.

## Inputs

Prefer semantic Markdown first, then JSON anchors:

- `outline_markdown` or `outline_markdown_path`
- `literature_report_markdown` or `literature_report_markdown_path`
- `outline.sections`, `logic_graph`, `argument_coverage`, `innovation_coverage`, `word_budget_plan`
- `literature_report.paper_reading_cards`, `argument_support_matrix`, `innovation_support_matrix`, `research_gaps`, `references`
- Optional `writing_task`, `research_data`, `user_claims`, `method_notes`, `experiment_notes`

If Markdown and JSON disagree, preserve the human-readable outline and literature report as the semantic source, then record the discrepancy in `open_questions` or `unsupported_claims`.

## Required Workflow

1. Build a global writing blueprint from the outline and literature report.
2. Convert each substantive outline section into a `section drafting card`.
3. Draft sections in Chinese academic prose, using `content-section-writer-agent` for long or batchable section work when available. Each section must make explicit argumentative moves: problem or claim, mechanism, evidence interpretation, comparison or tradeoff, limitation or boundary, and argument_return to the core argument or innovation point.
4. Integrate section drafts into one coherent paper: unify terms, transitions, citation numbering, and claim strength.
5. Before the deterministic script, run a citation reconciliation gate: freeze `draft.references[]`, build the reference id to numeric marker mapping, and ensure every `sections[].citations_used[]` entry has the corresponding marker near the supported claim in that section body.
6. Run the deterministic script as a contract gate. The script validates and packages prose; it does not call an LLM or invent missing content.

## Draft Contract

Required `draft` fields:

- `title`
- `abstract`
- `keywords`
- `sections[].title`
- `sections[].content_markdown`
- `sections[].citations_used`
- `references`

Recommended section fields:

- `source_outline_section_id`
- `target_word_count`
- `linked_core_arguments`
- `linked_innovation_points`
- `evidence_used`
- `data_used`
- `transition_in`
- `transition_out`
- `support_status`
- `section_depth_checks`

Recommended draft fields:

- `argument_trace`
- `innovation_trace`
- `unsupported_claims`
- `open_questions`
- `quality_checks`
- `draft_markdown`
- `draft_markdown_path`

`section_depth_checks` must contain:

- `problem_framed`
- `mechanism_explained`
- `evidence_interpreted`
- `comparison_or_tradeoff`
- `limitation_or_boundary`
- `argument_return`

Only mark these keys true when the body text contains the corresponding prose move.

## Evidence Rules

- Use only literature evidence from `literature_report`, extracted sources, user-provided research data, or explicit user claims.
- Search only when a needed claim is absent from `literature_report`; call `search_knowledge` and `extract_sources`, then cite the extracted evidence.
- Do not use snippets as strong evidence.
- Weakly supported claims must be written as limitations, gaps, trends, or open questions.
- Empirical results require `research_data`; missing data must become `open_questions`, not invented results.
- If `scripts/run.py` reports `content_markdown.citation_marker`, reconcile the section before reporting failure: add the expected marker to the specific supported sentence, or remove the unsupported citation from `citations_used` and the matching `evidence_used` entry.
- Do not append citation markers only to satisfy validation; each marker must remain semantically tied to a nearby claim.

## References

Load only the reference needed for the current step:

- `references/section-drafting-card.md` for section card shape.
- `references/section-depth-rubric.md` for preventing outline-like or list-only sections.
- `references/academic-prose-zh.md` for Chinese academic style.
- `references/citation-insertion.md` for `[n]` citation rules.
- `references/argument-consistency.md` for argument and innovation trace checks.
- `references/data-and-results-writing.md` for empirical/data claims.
- `references/word-budget-control.md` for section length control.

## Output

The script writes:

```json
{
  "artifact_type": "draft",
  "draft": {
    "title": "...",
    "abstract": "...",
    "keywords": [],
    "sections": [],
    "references": [],
    "draft_markdown": "...",
    "draft_markdown_path": "..."
  }
}
```

On failure, it writes `artifact_type: draft` with an `error` object listing blocking fields.
