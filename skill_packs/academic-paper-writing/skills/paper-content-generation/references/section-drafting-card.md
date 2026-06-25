# Section Drafting Card

A section drafting card is the unit passed to a section writer. It narrows the task so local generation cannot drift away from the outline.

Required fields:

- `source_outline_section_id`
- `title`
- `level`
- `target_word_count`
- `rhetorical_role`
- `linked_core_arguments`
- `linked_innovation_points`
- `allowed_references`
- `evidence_notes`
- `transition_in`
- `transition_out`

Recommended fields:

- `data_notes`
- `weak_or_open_claims`
- `forbidden_strong_claims`
- `style_notes`
- `depth_requirements`

The returned section draft must include `content_markdown`, `citations_used`, `evidence_used`, `data_used`, `support_status`, and `open_questions`. If the card marks evidence as weak, the section must use cautious language such as "仍需进一步验证", "可作为趋势判断", or "构成后续研究问题".

The returned section draft must also include `section_depth_checks` with:

- `problem_framed`
- `mechanism_explained`
- `evidence_interpreted`
- `comparison_or_tradeoff`
- `limitation_or_boundary`
- `argument_return`
