---
name: polish-and-plagiarism
description: 在 Skill5 formatted_draft 基础上润色正文、记录 polish_log 与降重建议，产出 polished_draft。Use when polish_and_plagiarism stage, formatted_draft exists, or user mentions 润色, 查重, 学术语气, polish_log, 降重. 不修正标题层级与引用格式（Skill5）；不重写论点或新增章节（Skill4）；不调用商业查重 API。
metadata: {"openclaw":{"requires":{"bins":["python"]}}}
---

# Polish and Plagiarism

## Scope

Use this skill only after a `formatted_draft` artifact exists (workflow stage `polish_and_plagiarism`). The deliverable is a `polished_draft` JSON artifact plus a final Markdown sidecar — the last prose stage before export or submission.

Do not use this skill to fix heading levels, unify `[n]` citation markers, or render GB/T 7714 bibliography entries. Those belong to Skill5 (`academic-formatting`). Do not rewrite core arguments, invent new sections, or regenerate references from scratch; those belong to upstream Skill4 (`paper-content-generation`).

This project does **not** integrate commercial plagiarism APIs. `plagiarism_optimization[]` is a structured list of similarity-reduction **suggestions** produced by the Agent from repetitive phrasing and common template wording; the script validates format and records them only.

| Role | Responsibility |
|------|----------------|
| **Agent** | Read `formatted_draft.markdown`, polish body prose, record `polish_log[]`, produce `plagiarism_optimization[]`; assemble the complete input JSON |
| **Deterministic script** (`scripts/run.py`) | Validate contract, diff against formatted draft, detect tone/citation/structure issues, emit `issues[]` and `quality_checks`; does not call an LLM or invent prose |

## Evidence Principles

- Preserve all factual claims and in-text `[n]` citation markers. Polish may adjust wording around citations but must not remove, renumber, or reorder markers when `preserve_citations` is true (default).
- Do not delete or rewrite `## 参考文献` entries. Only minor punctuation or whitespace adjustments around bibliography lines are acceptable.
- Every substantive edit must appear in `polish_log[]` with `section`, `change_type`, and `reason`. An empty log is a blocking failure (`polish_log_present`).
- Each entry in `protected_claims[]` must remain a **verbatim substring** of `polished_markdown`. Missing protected text causes exit code 1.
- Pass the **full** `formatted_draft` object (at least `markdown`) to the script so diff checks can run. Do not pass only `artifact_ref` or a partial diff.
- Record detected problems in `issues[]` with `severity: "warning"`. Structural contract failures (missing markdown, empty log, missing protected claims, markdown under 3000 characters) use exit code 1.

## Workflow

1. Inspect progress and confirm the `formatted_draft` artifact exists and `polish_and_plagiarism` is not already complete.
2. Read the full `formatted_draft.markdown`. If available, read `writing_task.target_journal.style_profile.tone` from upstream artifacts to align `polish_constraints.tone` (default `formal-zh`).
3. Read polish guides before editing:
   - `references/polish/academic-tone-zh.md` — formal Chinese tone, informal tokens to avoid
   - `references/polish/citation-preservation.md` — `[n]` markers and bibliography immutability
   - `references/polish/similarity-reduction.md` — `plagiarism_optimization[]` entry template and scope
4. Polish the paper text: improve fluency and objectivity, reduce cross-section repetitive phrasing, and note high-similarity spans for `plagiarism_optimization`. Do **not** change heading lines, citation indices, or bibliography entry text.
5. Prepare an input JSON matching `references/contracts/input.schema.json`. Include `polish_constraints`, `protected_claims`, `citation_constraints`, `polish_log`, and `plagiarism_optimization` when applicable. Example: `assets/input.example.json`.
6. Run the deterministic script:

```text
python skill_packs/academic-paper-writing/skills/polish-and-plagiarism/scripts/run.py --input path/to/input.json --output path/to/output.json
```

7. On success (exit 0), confirm the Markdown sidecar exists at `polished_draft.markdown_path` (same basename as the JSON output, `.md` extension).
8. Record the output with `update_artifact_manifest`, advance `polish_and_plagiarism` with `update_progress`, and summarize `polish_log` highlights, `plagiarism_optimization` suggestions, `issues[]`, `quality_checks`, and the Markdown path.

On failure (exit 1), read the `error` payload, fix blocking fields (`polished_markdown` missing, markdown too short, empty `polish_log`, missing `protected_claims` text), and re-run.

When `issues[]` contains `severity: "warning"` entries but exit code is 0, the script still wrote output. Fix tone or citation problems in `polished_markdown`, update `polish_log`, and re-run until `quality_checks` are acceptable or document remaining warnings explicitly.

## Input Contract

Required: `polished_markdown` (Agent-polished full paper Markdown, ≥3000 characters), `polish_log` (non-empty array). Strongly recommended: `formatted_draft.markdown` for diff validation.

Optional: `polish_constraints`, `protected_claims`, `citation_constraints`, `plagiarism_optimization`. Test-only: `accept_formatted_without_changes` (fallback to `formatted_draft.markdown` when `polished_markdown` is empty; `polish_log` must still be non-empty).

When `polish_constraints` is omitted, the script applies these defaults (aligned with `case/01-论文写作任务书.json`):

| Field | Default |
|-------|---------|
| `tone` | `formal-zh` |
| `language` | `zh` |
| `preserve_citations` | `true` |
| `preserve_headings` | `true` |

The Agent prepares:

```json
{
  "formatted_draft": {
    "markdown": "# 论文标题\n\n## 摘要\n\n…",
    "markdown_path": "path/to/formatted.md"
  },
  "polished_markdown": "Agent 润色后的完整 Markdown",
  "polish_constraints": {
    "tone": "formal-zh",
    "language": "zh",
    "preserve_citations": true,
    "preserve_headings": true
  },
  "protected_claims": [
    "大脑决策与 Skill 工具调用相结合的智能 Agent 系统"
  ],
  "citation_constraints": {
    "style": "numeric-bracket",
    "forbidden_changes": ["remove_marker", "renumber"]
  },
  "polish_log": [
    {
      "section": "引言",
      "change_type": "wording",
      "before": "其实很重要",
      "after": "具有关键意义",
      "reason": "去除口语化表达"
    }
  ],
  "plagiarism_optimization": [
    {
      "location": "相关工作",
      "risk": "high_similarity_phrase",
      "original": "大语言模型驱动的智能体正在重塑…",
      "suggestion": "改写为差异化表述并补充本文特有对比维度",
      "rewrite_hint": "突出 LangGraph + Skill 双轨架构差异"
    }
  ]
}
```

Schema: `references/contracts/input.schema.json`. Full sample: `assets/input.example.json`. Clean polished input: `assets/polished.sample.json`. Intentionally problematic input for testing: `assets/polished.raw.sample.json`. Formatted baseline: `assets/formatted_draft.sample.json`.

### `polish_log` entry fields

| Field | Required | Values / notes |
|-------|----------|----------------|
| `section` | yes | Section title or logical block |
| `change_type` | yes | `wording`, `deduplication`, `tone`, `clarity`, `other` |
| `reason` | yes | Why the change was made |
| `before` | no | Original phrase (may be truncated) |
| `after` | no | Revised phrase (may be truncated) |

### `plagiarism_optimization` entry fields

| Field | Required | Values / notes |
|-------|----------|----------------|
| `location` | yes | Section or paragraph |
| `risk` | yes | `high_similarity_phrase`, `cross_section_repetition`, `common_template_wording`, `other` |
| `suggestion` | yes | Recommended rewrite direction |
| `original` | no | Problematic source phrase |
| `rewrite_hint` | no | Paper-specific differentiation hint |

## Output Contract

On success the script writes:

```json
{
  "artifact_type": "polished_draft",
  "polished_draft": {
    "markdown": "# 论文标题\n\n## 摘要\n\n…",
    "markdown_path": "path/to/output.md",
    "polish_log": [
      {
        "section": "引言",
        "change_type": "wording",
        "before": "其实很重要",
        "after": "具有关键意义",
        "reason": "去除口语化表达"
      }
    ],
    "plagiarism_optimization": [],
    "issues": [
      {
        "code": "informal_tone",
        "severity": "warning",
        "field": "polished_markdown",
        "message": "informal or non-academic expressions detected: 其实"
      }
    ],
    "quality_checks": {
      "tone_academic": false,
      "polish_log_present": true
    },
    "source_formatted_path": "path/to/formatted.md"
  }
}
```

On failure:

```json
{
  "artifact_type": "polished_draft",
  "error": {
    "message": "polish_log must be a non-empty array of edit records",
    "fields": ["polish_log"]
  }
}
```

Inner object schema: `references/contracts/polished-draft.schema.json`. Pack envelope: `schemas/polish_report.schema.json`.

### Blocking validations (exit 1)

| Check | Field(s) |
|-------|----------|
| `polished_markdown` present and non-empty | `polished_markdown` |
| Markdown length ≥ 3000 characters | `polished_markdown` |
| `polish_log` non-empty; each entry has `section`, `change_type`, `reason` | `polish_log` |
| Every `protected_claims[]` entry is a substring of polished markdown | `protected_claims[n]` |

### `issues[]` codes

| Code | Typical severity | Meaning |
|------|------------------|---------|
| `heading_structure_changed` | `warning` | Heading lines (`^#{1,6}\s`) differ from `formatted_draft.markdown` |
| `citation_marker_changed` | `warning` | Body `[n]` marker multiset differs from formatted draft |
| `bibliography_changed` | `warning` | `## 参考文献` entry lines differ (whitespace-normalized) |
| `informal_tone` | `warning` | Colloquial tokens, exclamation marks, or marketing tone detected |
| `repetitive_phrasing` | `warning` | Identical sentence fragment ≥20 characters appears more often than in formatted draft |

Diff checks run only when `formatted_draft.markdown` is provided. Informal-tone and repetition checks always run on `polished_markdown`.

### `quality_checks`

Aligned with `workflow.yaml` stage checks:

- `polish_log_present` — `true` when `polish_log` is non-empty and every entry has `section`, `change_type`, and `reason`
- `tone_academic` — `true` when no unresolved `warning` remains for `informal_tone`, `citation_marker_changed`, `bibliography_changed`, `heading_structure_changed`, or `repetitive_phrasing`

Unresolved warnings do not change exit code (still 0) but set `tone_academic` to `false`. The Agent should fix or explicitly report them.

### Preserved Markdown structure

Skill6 must leave these blocks unchanged relative to Skill5 output:

| Block | Rule |
|-------|------|
| Title and section headings | Same `#` … `######` lines as formatted draft |
| In-text citations | Same `[n]` indices and counts in body (before `## 参考文献`) |
| Bibliography | Same `## 参考文献` heading and entry lines |
| Keywords line | May polish surrounding prose only; do not remove the keywords block |

## Final Checks

Before reporting completion, verify:

- `artifact_type` is `polished_draft` and the script exited 0.
- `polished_draft.markdown` is non-empty and the `.md` sidecar file exists at `markdown_path`.
- Rendered Markdown length is at least 3000 characters (blocking gate).
- `quality_checks.polish_log_present` is `true` — `polish_log` is non-empty and structurally valid.
- `quality_checks.tone_academic` is `true` — no unresolved informal tone, citation, heading, bibliography, or repetition warnings.
- Every `protected_claims` string still appears verbatim in the polished markdown.
- In-text `[n]` markers and `## 参考文献` entries match the formatted draft (when diff checks ran).
- `plagiarism_optimization` suggestions are summarized for the user; clarify that no external plagiarism API was called.
- Key `polish_log` entries are mentioned in the Agent summary so the user knows what wording changed.
- Unresolved `severity: "warning"` items in `issues[]` are listed explicitly; do not claim full academic-tone compliance while warnings remain.
- The final Markdown sidecar is suitable for export without further Skill5 formatting passes.
