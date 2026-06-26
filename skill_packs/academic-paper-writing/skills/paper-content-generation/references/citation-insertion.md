# Citation Insertion

Use bracketed numeric citations in body prose: `[1]`, `[2]`, `[3]`.

Rules:

- `draft.references[]` order defines citation numbers.
- `sections[].citations_used[]` may store reference ids such as `zero2020` or numeric strings such as `"2"`.
- A section that lists `citations_used: ["zero2020"]` must contain the corresponding marker for that reference index. A section that lists `citations_used: ["2"]` must contain `[2]`.
- Before running the deterministic script, build a reference id to numeric marker map and verify every `citations_used[]` entry appears in that section's body markers.
- If a declared citation is missing from the body, add the marker only to the sentence supported by that source, or remove the citation and matching evidence entry.
- Do not append citation markers only to satisfy validation.
- Do not cite a paper that is absent from `draft.references[]`.
- Do not invent DOI, page range, author, venue, or URL values.
- If a claim comes from a newly searched source, add that source to `references[]` and record it in `evidence_used`.

Reference objects should prefer `id`, `title`, `authors`, `year`, `venue`, `url`, `doi`, and a rendered `gb7714` or `apa` field when available.
