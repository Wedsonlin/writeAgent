# Citation Preservation

Rules for keeping in-text markers and bibliography intact during Skill6 polish.

Skill5 (`academic_formatting`) normalizes citations to `[n]` and renders `## 参考文献`. Skill6 **must not undo** that work.

## Scope Boundary

| Element | Skill6 may change | Skill6 must not change |
|---------|-------------------|------------------------|
| Body prose around citations | Yes (wording, deduplication) | — |
| In-text `[n]` markers | Punctuation/spacing adjacent to marker only | Remove, renumber, or reorder markers |
| Heading lines (`^#{1,6}\s`) | No | Add, remove, rename, or reorder headings |
| `## 参考文献` block entries | No | Delete, merge, or rewrite bibliography lines |
| `protected_claims[]` text | No | Omit or alter protected factual strings |

When `polish_constraints.preserve_citations` or `preserve_headings` is `true` (default), the script diffs `formatted_draft.markdown` against `polished_markdown`.

## In-Text Markers

Canonical form: **`[n]`** where `n` is a positive integer (see Skill5 [`in-text-citation-rules.md`](../../academic-formatting/references/formatting/in-text-citation-rules.md)).

Allowed micro-edits near markers:

- Adjust Chinese punctuation before/after a marker: `…质量[1]。` ↔ `…质量[1].` (prefer full-width `。` in Chinese body text).
- Normalize accidental spaces: `[ 1 ]` → `[1]` only if Skill5 already emitted `[1]` in formatted draft — do not invent new numbers.

Forbidden (`citation_constraints.forbidden_changes`):

| Code | Meaning |
|------|---------|
| `remove_marker` | Citation present in formatted draft but missing in polished body |
| `renumber` | Same prose context but different `[n]` index |
| `reorder_bibliography` | Bibliography line set differs (see below) |

Script issue code: `citation_marker_changed` (severity `warning`).

## Bibliography Block

Everything after the heading line `## 参考文献` is compared as a **set of non-empty lines** (whitespace ignored).

Rules:

- Each entry line must remain present with the same `[n]` prefix and core bibliographic content.
- Do not drop entries, swap `[1]`/`[2]` labels, or rewrite author/title/venue strings during polish.
- If bibliography fixes are needed, return to Skill5 — not Skill6.

Script issue code: `bibliography_changed` (severity `warning`).

## Headings

All Markdown heading lines extracted with pattern `^#{1,6}\s` must match **exactly** between formatted and polished drafts when `preserve_headings: true`.

Examples of violations:

- Title changed from `# 面向学术论文写作的智能 Agent 设计与实现` to `# 智能写作 Agent 系统（润色稿）`
- Section removed or renamed (`## 引言` → `## 背景`)

Script issue code: `heading_structure_changed` (severity `warning`).

## Protected Claims

Input field `protected_claims[]` lists factual assertions that must survive polish verbatim (substring match in `polished_markdown`).

Use for:

- Core contribution statements
- Reported experimental conclusions
- Legally or ethically sensitive claims

Missing protected text is a **blocking** error (`protected_claim_missing`) in script validation.

## Agent Checklist

1. Pass full `formatted_draft.markdown` in the Skill input JSON for diff checks.
2. Set `citation_constraints.style` to `numeric-bracket` when using `[n]`.
3. After polishing, scan body text for every `[n]` in the formatted draft — each must still appear.
4. Do not edit lines under `## 参考文献`.
5. Record citation-adjacent wording changes in `polish_log` but never log citation number changes (there should be none).

## Quality Check

`quality_checks.tone_academic` incorporates citation and heading preservation: any unresolved `citation_marker_changed`, `bibliography_changed`, or `heading_structure_changed` warning keeps it `false`.
