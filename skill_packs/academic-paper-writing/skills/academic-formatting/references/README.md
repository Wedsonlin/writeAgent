# References for academic-formatting

Deterministic contracts and style guides for Skill5 (`academic_formatting`).

## Contracts

| File | Purpose |
|------|---------|
| [`contracts/input.schema.json`](contracts/input.schema.json) | Script input: `draft` + optional `formatting_constraints` |
| [`contracts/formatted-draft.schema.json`](contracts/formatted-draft.schema.json) | Inner `formatted_draft` object written by `scripts/run.py` |

## Formatting Guides

| File | Topic |
|------|-------|
| [`formatting/heading-rules.md`](formatting/heading-rules.md) | Title / abstract / section heading levels; no level jumps |
| [`formatting/in-text-citation-rules.md`](formatting/in-text-citation-rules.md) | Normalize body citations to `[n]` |
| [`formatting/gb7714-bibliography.md`](formatting/gb7714-bibliography.md) | GB/T 7714 bibliography list with `[n]` prefix |

Pack-level envelope schema: [`schemas/format_report.schema.json`](../../../schemas/format_report.schema.json).

## Examples

- [`../assets/input.example.json`](../assets/input.example.json) — full input sample
- [`../assets/draft.sample.json`](../assets/draft.sample.json) — clean draft
- [`../assets/draft.raw.sample.json`](../assets/draft.raw.sample.json) — draft with intentional format defects
