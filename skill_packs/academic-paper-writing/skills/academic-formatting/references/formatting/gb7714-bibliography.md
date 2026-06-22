# GB/T 7714 Bibliography Rules

Bibliography formatting for the `academic_formatting` stage. Entry field rules follow Skill2:

- See [`literature-review/references/citation/gb7714-rules.md`](../../../literature-review/references/citation/gb7714-rules.md) for type marks, author display, and metadata handling.

This document adds **reference-list rendering** rules used when producing `formatted_draft.markdown`.

## Entry Generation

For each `draft.references[]` object with structured fields (`authors`, `title`, `year`, `type`, …):

1. Prefer an existing `gb7714` string when present and non-empty.
2. Otherwise call the shared `format_bibliography` helper (same implementation as Skill2 `cite.py`).
3. Write the generated string back to `normalized_draft.references[].gb7714`.

Do not invent DOI, authors, venues, or page ranges not present in the source metadata.

## Rendered List Format

Under the `## 参考文献` heading, each line uses:

```text
[n] <gb7714 entry>
```

Where:

- `n` is the 1-based index in `references[]`.
- `<gb7714 entry>` is the `gb7714` field (generated or pre-existing).
- No extra brackets wrap the bibliography text beyond the leading `[n]` prefix.

Example:

```text
## 参考文献

[1] Yao S, Zhao J, Yu D, 等. ReAct: Synergizing Reasoning and Acting in Language Models[EB/OL]. arXiv preprint arXiv:2210.03629, 2022. DOI:10.48550/arXiv.2210.03629.
[2] Schick T, Dwivedi-Yu J, Dessi R, 等. Toolformer: Language Models Can Teach Themselves to Use Tools[EB/OL]. arXiv preprint arXiv:2302.04761, 2023.
```

## String-Only References

If a reference is a plain string, render it as `[n] {string}` without attempting GB/T field inference.

## Fallback Order

When choosing display text for a reference object, use this priority:

1. `gb7714`
2. `text`
3. `citation`
4. `title` (last resort)

## Issues

| Code | Severity | Meaning |
|------|----------|---------|
| `missing_gb7714` | `fixed` or `warning` | Entry lacked `gb7714`; script attempted generation |
| `gb7714_generation_failed` | `warning` | Structured fields insufficient to build an entry |

## Quality Check

`quality_checks.references_formatted` is `true` when every list entry has renderable GB/T text and in-text `[n]` markers align with the bibliography (see `in-text-citation-rules.md`).
