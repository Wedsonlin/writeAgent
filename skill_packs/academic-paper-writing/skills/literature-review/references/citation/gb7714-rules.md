# GB/T 7714 Formatting Rules

The script implements a compact deterministic subset for writeAgent artifacts.

## Type Marks

- Journal: `[J]`
- Conference: `[C]`
- Preprint or online source: `[EB/OL]`
- Miscellaneous documentation: `[Z]`

## Author Display

- Show up to three authors.
- If there are more than three authors, append `等`.
- Do not invent missing authors; use `Unknown` if metadata is absent.

## Metadata

- Preserve DOI when available: `DOI:<value>`.
- Preserve URL when DOI is absent.
- Leave unknown venue as `Unknown venue`; do not infer it from title.
