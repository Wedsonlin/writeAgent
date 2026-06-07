# Source Evidence Labels

Use these labels inside `source_map[].provenance`.

- `abstract`: statement appears in the BibTeX abstract or supplied paper abstract.
- `metadata`: title, author, year, venue, DOI, or URL metadata.
- `原文`: statement appears in the paper text or extracted notes.
- `用户确认`: the user confirmed the interpretation.
- `推断`: the Agent inferred it from method, scope, or missing evaluation.
- `建议`: a reuse idea or future-work suggestion, not an original claim.

Rules:

- `key_claims[]` should be original-source or user-confirmed when possible.
- `research_gaps[]` may include inference, but must not be phrased as if authors stated it.
- Do not invent paper findings from titles alone.
