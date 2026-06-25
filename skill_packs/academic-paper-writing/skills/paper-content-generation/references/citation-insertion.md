# Citation Insertion

Use bracketed numeric citations in body prose: `[1]`, `[2]`, `[3]`.

Rules:

- `draft.references[]` order defines citation numbers.
- `sections[].citations_used[]` stores reference ids such as `zero2020`, not numeric strings.
- A section that lists `citations_used: ["zero2020"]` must contain the corresponding marker for that reference index.
- Do not cite a paper that is absent from `draft.references[]`.
- Do not invent DOI, page range, author, venue, or URL values.
- If a claim comes from a newly searched source, add that source to `references[]` and record it in `evidence_used`.

Reference objects should prefer `id`, `title`, `authors`, `year`, `venue`, `url`, `doi`, and a rendered `gb7714` or `apa` field when available.
