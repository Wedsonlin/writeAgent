# Literature Claims Extraction Sub-agent Prompt

Extract structured claims from the provided papers or reference context.

Return a JSON object with:
- `paper_claims`: array of paper records

Each paper claim should include:
- `id` or `paper_id`
- `key_claims`
- `evidence_strength`
- `limitations`
- `methods`

Do not format citations and do not write the final literature report.
