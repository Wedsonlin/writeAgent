# Coverage Rubric

Use this rubric before building `source_map[]` and the support matrices.

## Inputs To Cover

- Task book Markdown: topic, problem framing, confirmed constraints, and research direction wording.
- JSON anchors: `core_arguments`, `innovation_points`, `research_scope`, `references_seed`, and `argument_evidence_matrix`.
- Explicit `research_keywords` when present.

## Enough Coverage

Treat seed references as sufficient only when all conditions hold:

- Each core argument has at least one directly relevant paper and one background or extension paper in `paper_reading_cards[]`.
- Each innovation point has at least one representative system, method, trend, benchmark, or engineering trade-off source.
- Each research keyword or subtopic is represented by at least one credible source.
- The bibliography includes field-defining work and recent work, unless the task book explicitly asks for a historical or theoretical review.
- Key claims can be grounded in extracted source text, paper abstracts, or user-provided notes, not titles alone.
- `strong` or `moderate` support has both `source_urls` and `source_artifact_ids`; search snippets alone count only as weak discovery evidence.
- Weak sources such as blog posts, project pages, or metadata-only records do not dominate the evidence base.

## Insufficient Coverage

Actively search for more papers when:

- `references_seed` is empty or mostly non-paper material.
- A core argument has no supporting or contrasting paper.
- An innovation point has no supporting representative paper or system.
- A research keyword appears only in the task book and not in the candidate papers.
- All available sources are metadata-only.
- There are no sources for controversies, limitations, or research gaps.

Record remaining gaps as weak evidence or `unmapped_papers`; do not fill them with invented claims.
