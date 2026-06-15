---
name: academic-formatting
description: 将 Skill4 产出的 draft 规范为期刊体例的 formatted_draft，含标题层级修正、正文 [n] 引用统一与 GB/T 7714 参考文献列表。Use when academic_formatting stage, draft exists, or user mentions 格式规范, 标题层级, 参考文献, GB7714, 引用标注. 不润色正文、不重写论点；格式修正须保留 issues[] 记录。
metadata: {"openclaw":{"requires":{"bins":["python"]}}}
---

# Academic Formatting

## Scope

Use this skill only after a `draft` artifact exists (workflow stage `academic_formatting`). The deliverable is a `formatted_draft` JSON artifact plus a Markdown sidecar that downstream `polish-and-plagiarism` consumes.

Do not use this skill to polish prose, reduce similarity, rewrite arguments, or generate new sections. Those belong to Skill6 (`polish-and-plagiarism`) or upstream Skill4 (`paper-content-generation`).

| Role | Responsibility |
|------|----------------|
| **Agent** | Read the full `draft`, apply journal constraints to headings, in-text citations, and bibliography entries; assemble the complete input JSON |
| **Deterministic script** (`scripts/run.py`) | Validate contract, normalize headings and citations, render Markdown, emit `issues[]` and `quality_checks`; does not call an LLM |

## Evidence Principles

- Preserve all substantive claims, data, and reference metadata. Format fixes must not delete or rewrite body arguments.
- Do not invent DOI, authors, venues, page ranges, or citation numbers not grounded in `draft.references[]`.
- Record every automatic correction in `issues[]` with `severity: "fixed"`. Unresolvable problems use `severity: "warning"`; structural failures use exit code 1.
- Default to Chinese journal presentation (`GB/T 7714`, `## 摘要`, numeric `[n]` citations) when `formatting_constraints` is omitted.
- Pass the **full** `draft` object to the script after any Agent-side edits. Do not pass only `artifact_ref` or a diff.

## Workflow

1. Inspect progress and confirm the `draft` artifact exists and `academic_formatting` is not already complete.
2. Read the full `draft` (`title`, `abstract`, `keywords`, `sections[]`, `references[]`). If available, read `writing_task.target_journal.style_profile` from upstream artifacts for citation and heading preferences.
3. Read formatting guides before editing:
   - `references/formatting/heading-rules.md` — section levels, abstract heading, no level jumps
   - `references/formatting/in-text-citation-rules.md` — canonical `[n]` markers
   - `references/formatting/gb7714-bibliography.md` — bibliography list rendering (field rules in Skill2 `literature-review/references/citation/gb7714-rules.md`)
4. Correct format problems in the draft where the Agent can do so safely: fix heading levels, unify `(n)` / `[n]`混用,补全或校对 `references[].gb7714` when structured fields exist.
5. Prepare an input JSON matching `references/contracts/input.schema.json`. Include `formatting_constraints` when the target journal deviates from defaults (see Input Contract). Example: `assets/input.example.json`.
6. Run the deterministic script:

```text
python skill_packs/academic-paper-writing/skills/academic-formatting/scripts/run.py --input path/to/input.json --output path/to/output.json
```

7. On success (exit 0), confirm the Markdown sidecar exists at `formatted_draft.markdown_path` (same basename as the JSON output, `.md` extension).
8. Record the output with `update_artifact_manifest`, advance `academic_formatting` with `update_progress`, and summarize `issues[]`, `quality_checks`, and the Markdown path.

On failure (exit 1), read the `error` payload, fix blocking fields (`draft` missing, empty `sections`, Markdown under 3000 characters), and re-run.

## Input Contract

Required: `draft` (full Skill4 draft object). Optional: `formatting_constraints`.

When `formatting_constraints` is omitted, the script applies these defaults (aligned with `case/01-论文写作任务书.md`):

| Field | Default |
|-------|---------|
| `citation_style` | `GB/T 7714` |
| `heading_rules.max_level` | `3` |
| `heading_rules.abstract_heading` | `## 摘要` |
| `reference_rules.in_text_style` | `numeric-bracket` (`[n]`) |
| `reference_rules.bibliography_style` | `gb7714` |
| `export_format` | `markdown` |

The Agent prepares:

```json
{
  "draft": {
    "title": "论文标题",
    "abstract": "摘要正文…",
    "keywords": ["关键词1", "关键词2"],
    "sections": [
      {
        "id": "1",
        "title": "引言",
        "level": 1,
        "content_markdown": "正文…引用标注使用 [1]…",
        "citations_used": ["yao2022react"],
        "word_count": 400
      }
    ],
    "references": [
      {
        "id": "yao2022react",
        "type": "preprint",
        "title": "ReAct: Synergizing Reasoning and Acting in Language Models",
        "authors": ["Shunyu Yao", "Jeffrey Zhao"],
        "year": 2022,
        "venue": "arXiv preprint arXiv:2210.03629",
        "doi": "10.48550/arXiv.2210.03629",
        "gb7714": "Yao S, Zhao J, …"
      }
    ],
    "open_questions": []
  },
  "formatting_constraints": {
    "citation_style": "GB/T 7714",
    "heading_rules": {"max_level": 3, "abstract_heading": "## 摘要"},
    "reference_rules": {"in_text_style": "numeric-bracket", "bibliography_style": "gb7714"},
    "export_format": "markdown"
  }
}
```

Schema: `references/contracts/input.schema.json`. Full sample: `assets/input.example.json`. Clean draft only: `assets/draft.sample.json`. Intentionally messy draft for testing: `assets/draft.raw.sample.json`.

## Output Contract

On success the script writes:

```json
{
  "artifact_type": "formatted_draft",
  "formatted_draft": {
    "normalized_draft": {"title": "...", "abstract": "...", "keywords": [], "sections": [], "references": []},
    "markdown": "# 论文标题\n\n## 摘要\n\n…",
    "markdown_path": "path/to/output.md",
    "issues": [
      {
        "code": "heading_level_jump",
        "severity": "fixed",
        "field": "draft.sections[2].level",
        "message": "heading level jumps from 1 to 3; remapped to 2"
      }
    ],
    "quality_checks": {
      "headings_normalized": true,
      "references_formatted": true
    }
  }
}
```

On failure:

```json
{
  "artifact_type": "formatted_draft",
  "error": {
    "message": "draft.sections is required",
    "fields": ["draft.sections"]
  }
}
```

Inner object schema: `references/contracts/formatted-draft.schema.json`. Pack envelope: `schemas/format_report.schema.json`.

### `issues[]` codes

| Code | Typical severity | Meaning |
|------|------------------|---------|
| `heading_level_jump` | `fixed` / `warning` | Section `level` skipped a nesting step or exceeds `max_level` |
| `missing_section_title` | `warning` | Empty `sections[].title`; section skipped in render |
| `citation_style_inconsistent` | `fixed` / `warning` | Body used `(n)`, `[[n]]`, or other non-canonical markers |
| `missing_gb7714` | `fixed` / `warning` | Bibliography entry lacked `gb7714`; script attempted generation |
| `gb7714_generation_failed` | `warning` | Structured fields insufficient to build GB/T entry |
| `citation_id_unmapped` | `warning` | `citations_used` id not found in `references[]` |
| `citation_index_out_of_range` | `warning` | `[n]` in body does not match `references[]` length |

Auto-fixable items are normalized before final detection; remaining `warning` entries drive `quality_checks`.

### `quality_checks`

Aligned with `workflow.yaml` stage checks:

- `headings_normalized` — `true` when no unresolved `heading_level_jump` or `missing_section_title` warnings remain
- `references_formatted` — `true` when no unresolved citation or bibliography warnings remain (`citation_style_inconsistent`, `missing_gb7714`, `citation_id_unmapped`, `citation_index_out_of_range`)

### Rendered Markdown layout

| Block | Source | Markdown |
|-------|--------|----------|
| Title | `draft.title` | `# {title}` |
| Abstract | `draft.abstract` | `## 摘要` (or `abstract_heading`) |
| Keywords | `draft.keywords` | `**关键词**：…` |
| Body | `sections[].title` + `level` | `##` … `######` via `level + 1` |
| References | `references[]` | `## 参考文献` then `[n] <gb7714>` per line |

Do not add 摘要 or 参考文献 as regular `sections[]` entries.

## Final Checks

Before reporting completion, verify:

- `artifact_type` is `formatted_draft` and the script exited 0.
- `formatted_draft.markdown` is non-empty and the `.md` sidecar file exists at `markdown_path`.
- Rendered Markdown length is at least 3000 characters (blocking gate).
- `quality_checks.headings_normalized` is `true` — section levels are continuous, within `max_level`, and no empty titles block rendering.
- `quality_checks.references_formatted` is `true` — body citations use `[n]`, list order matches `references[]`, and each entry has renderable GB/T text.
- `normalized_draft` retains the paper title, abstract, all substantive sections, and the full reference list.
- Every `severity: "fixed"` issue in `issues[]` is mentioned in the Agent summary so the user knows what changed automatically.
- Unresolved `severity: "warning"` items are listed explicitly; do not claim full formatting compliance while warnings remain.
- Downstream Skill6 can read `formatted_draft.markdown` without additional transformation.
