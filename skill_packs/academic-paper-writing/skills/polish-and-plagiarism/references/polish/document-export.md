# Final Document Export

Skill6 produces the final deliverable manuscript. It must re-export the polished manuscript instead of reusing Skill5's DOCX.

## Required Files

- JSON: `polished_draft` envelope.
- Markdown: `polished_draft.markdown_path`.
- DOCX: `polished_draft.docx_path`.

DOCX is required. If DOCX generation fails, Skill6 should fail with an `error` payload.

## Optional PDF

PDF is best-effort. If PDF cannot be generated, record:

```json
{
  "pdf": {
    "status": "unavailable",
    "path": null,
    "reason": "..."
  }
}
```

## Finality

The DOCX exported by Skill6 is the final manuscript artifact for the six-stage workflow. Skill5's DOCX is only an intermediate formatted version.
