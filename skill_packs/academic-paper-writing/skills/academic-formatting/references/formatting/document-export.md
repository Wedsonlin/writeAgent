# Document Export Rules

Skill5 must emit both machine-readable JSON and human-readable/export files.

## Required Files

- JSON: `formatted_draft` envelope.
- Markdown: `formatted_draft.markdown_path`.
- DOCX: `formatted_draft.docx_path`.

DOCX export is required. If DOCX generation fails, the skill should fail with an `error` payload instead of claiming success.

## Optional PDF

PDF is best-effort. If the environment lacks `reportlab`, a usable Chinese font, or PDF rendering support, keep the skill successful and record:

```json
{
  "pdf": {
    "status": "unavailable",
    "path": null,
    "reason": "..."
  }
}
```

## Formatting Defaults

- Body font: Chinese academic default such as SimSun when available.
- Body size: approximately 12 pt.
- Line spacing: 1.5.
- Headings: Word heading styles where possible.
- References: numbered lines preserved as `[n] ...`.

The exported DOCX/PDF is an intermediate formatted manuscript. Skill6 must re-export the final polished manuscript.
