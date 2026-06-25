# Protected Claims

Protected claims are core arguments, innovation points, evidence conclusions, or exact user-approved formulations that must survive polishing.

## Rules

- If `protected_claims[]` is provided, every entry must remain a verbatim substring of `polished_markdown`.
- If a protected claim is awkwardly worded but user-approved, keep it and improve surrounding transitions instead.
- Do not weaken or strengthen protected claims unless the input explicitly asks for a change.
- Do not move a weakly supported claim into a strong conclusion just to improve rhetorical flow.

## Safe Edits Around Protected Claims

- Add transition sentences before or after the claim.
- Remove repeated phrasing in neighboring sentences.
- Clarify the evidence source while keeping the protected text intact.

If a protected claim appears factually unsupported, preserve it and add an `issues[]` warning or a `plagiarism_optimization[]` note rather than rewriting it silently.
