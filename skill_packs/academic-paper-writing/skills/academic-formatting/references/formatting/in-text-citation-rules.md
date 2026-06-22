# In-Text Citation Rules

Numeric bracket citations for Chinese journal-style papers in this workflow.

## Canonical Form

All in-text markers normalize to **`[n]`** where `n` is a positive integer matching the **1-based index** of the cited entry in `draft.references[]`.

Examples:

| Before (non-canonical) | After |
|------------------------|-------|
| `(1)` | `[1]` |
| `[(1)]` | `[1]` |
| `[[1]]` | `[1]` |
| `[ 1 ]` | `[1]` |
| `(2)` | `[2]` |

## Ordering

- Reference list order in `draft.references[]` defines citation numbers.
- The first entry is `[1]`, the second `[2]`, and so on.
- Reordering `references[]` requires updating all in-text markers accordingly.

## `citations_used` Alignment

Each `sections[].citations_used[]` entry should be a `references[].id` string (e.g. `yao2022react`).

The script cross-checks:

- Every `citations_used` id exists in `references[]`.
- Numeric markers in `content_markdown` map to a valid list index.

Mismatches are recorded in `issues[]` as warnings (`citation_id_unmapped`, `citation_index_out_of_range`) but do not block output unless structural draft checks fail.

## Agent Responsibilities

- Prefer `[n]` in new or revised prose.
- When merging sections, deduplicate references at the list level rather than reusing conflicting numbers in body text.
- Do not invent citation numbers without a corresponding `references[]` entry.

## Quality Check

`quality_checks.references_formatted` is `true` when in-text markers are normalized and no unresolved citation warnings remain.
