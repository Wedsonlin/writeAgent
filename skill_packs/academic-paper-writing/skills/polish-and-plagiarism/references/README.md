# References for polish-and-plagiarism

Deterministic contracts and style guides for Skill6 (`polish_and_plagiarism`).

## Contracts

| File | Purpose |
|------|---------|
| [`contracts/input.schema.json`](contracts/input.schema.json) | Script input: `polished_markdown` + optional `formatted_draft`, constraints, logs |
| [`contracts/polished-draft.schema.json`](contracts/polished-draft.schema.json) | Inner `polished_draft` object written by `scripts/run.py` |

## Polish Guides

| File | Topic |
|------|-------|
| [`polish/academic-tone-zh.md`](polish/academic-tone-zh.md) | Formal Chinese academic tone; informal phrase avoidance |
| [`polish/citation-preservation.md`](polish/citation-preservation.md) | Preserve `[n]` markers, headings, and bibliography |
| [`polish/similarity-reduction.md`](polish/similarity-reduction.md) | `plagiarism_optimization[]` template; no external API |

Pack-level envelope schema: [`schemas/polish_report.schema.json`](../../../schemas/polish_report.schema.json).

## Examples

- [`../assets/input.example.json`](../assets/input.example.json) — full input sample
- [`../assets/polished.sample.json`](../assets/polished.sample.json) — clean polished input
- [`../assets/polished.raw.sample.json`](../assets/polished.raw.sample.json) — input with intentional tone/citation defects
