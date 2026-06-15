# Academic Tone (Chinese)

Formal Chinese academic prose rules for Skill6 (`polish_and_plagiarism`).

Skill6 improves fluency and objectivity **after** Skill5 has normalized headings, citations, and bibliography. Do not reformat structure here; focus on wording.

## Target Tone

Default constraint: `polish_constraints.tone = formal-zh` (aligns with `writing_task.target_journal.style_profile.tone`).

Characteristics:

- **Objective and impersonal** — prefer third-person or subject-neutral constructions (`本文`, `本系统`, `实验结果表明`).
- **Precise and restrained** — state claims with appropriate hedging where evidence is indirect (`表明`, `显示`, `在一定程度上`).
- **Consistent register** — same section should not mix colloquial fragments with formal passages.

## Avoid (Informal / Non-Academic)

| Category | Examples | Preferred direction |
|----------|----------|---------------------|
| Colloquial fillers | 其实、挺、超级、蛮、搞定、说白了 | Remove or replace with neutral phrasing |
| Subjective intensifiers | 我觉得、我们认为（过度使用）、非常非常好 | 实验表明 / 本文认为（限摘要贡献句） |
| Exclamation marks | `！` in body text | Use period `。` only |
| Chatty connectors | 然后呢、话说回来、总之呢 | 此外、因此、综上所述 |
| Over-first-person | 我、咱们、你 | 本文、本研究、用户（当指代明确时） |
| Marketing tone | 颠覆性、革命性、最强 | 显著、有效、具有优势（需有依据） |

The deterministic script flags known informal tokens as `informal_tone` (severity `warning`), which sets `quality_checks.tone_academic` to `false`.

## Encourage

- **Nominalization where natural**: 「进行了分析」→「开展分析」或保留动宾结构，避免口语化「去分析了一下」。
- **Parallel structure** in enumerations and contrast pairs.
- **Section-appropriate openings**: 引言交代背景与动机；相关工作客观综述；结论避免引入新论据。
- **Concise transitions**: 与此同时、据此、在此基础上 — instead of repeating entire template paragraphs across sections.

## Repetitive Phrasing

Long identical spans (≥20 characters) appearing in two or more places are flagged as `repetitive_phrasing`. When polishing:

- Rewrite duplicated boilerplate per section with section-specific focus.
- Keep shared factual claims and `[n]` citations intact.
- Record deduplication edits in `polish_log` with `change_type: deduplication`.

## Agent Responsibilities

1. Read `formatted_draft.markdown` and `polish_constraints` before editing.
2. Polish body prose only; do not change heading lines or reference entries (see [`citation-preservation.md`](citation-preservation.md)).
3. Log every substantive wording change in `polish_log[]` with `section`, `change_type`, and `reason`.
4. Preserve every string in `protected_claims[]` as an exact substring of `polished_markdown`.

## Quality Check

`quality_checks.tone_academic` is `true` when the script finds no unresolved warnings among:

- `informal_tone`
- `citation_marker_changed`
- `bibliography_changed`
- `heading_structure_changed`
- `repetitive_phrasing`

Agent polish remains the primary quality lever; the script provides an automatable gate, not a substitute for human review.
