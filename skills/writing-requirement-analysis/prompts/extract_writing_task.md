# Requirement Analysis Sub-agent Prompt

Convert the user request into a structured writing task JSON object.

Required fields:
- `topic`
- `paper_type`
- `language`
- `target_journal`
- `word_limit`
- `core_arguments`
- `innovation_points`
- `research_scope`
- `chapter_framework`
- `references_seed`
- `missing_info`

If critical information is missing, include it in `missing_info` instead of asking the user directly.
