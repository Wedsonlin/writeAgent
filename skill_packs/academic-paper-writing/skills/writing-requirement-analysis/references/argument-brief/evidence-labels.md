# Evidence Labels

Source note: adapted from the evidence discipline in `zLanqing/codex-claude-academic-skills`, rewritten for writeAgent artifacts.

Use these labels when preparing `provenance` and when summarizing unresolved assumptions.

## Labels

- `原文/已有数据`: The user supplied it directly in a document, requirement, case file, artifact, or reference.
- `用户确认`: The user confirmed it through `ask_user` or a direct instruction.
- `推断`: The Agent inferred it from surrounding context. Use sparingly and keep it reversible.
- `建议`: A recommended default or next-step suggestion, not a fact.

## Rules

- Critical writing-task fields should be `原文/已有数据` or `用户确认`.
- Do not treat inferred venue rules as facts unless the profile file contains them.
- Do not invent journal policies, page limits, DOI values, experimental results, or author claims.
- If a field remains uncertain but non-blocking, include it in `missing_info` rather than silently guessing.

## Minimum Provenance

Record provenance for:

- `core_claim`
- `contributions`
- `venue`
- `word_limit`
- `scope.boundary`
- `references_seed`
