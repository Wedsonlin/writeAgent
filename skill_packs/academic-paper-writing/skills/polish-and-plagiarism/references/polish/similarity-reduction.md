# Similarity Reduction

Structured guidance for `plagiarism_optimization[]` in Skill6 (`polish_and_plagiarism`).

## Scope

This workflow **does not call external plagiarism or duplicate-detection APIs** (per project case boundary). The Agent identifies likely similarity risks heuristically — repeated template sentences, common LLM phrasing, cross-section duplication — and records actionable suggestions in `plagiarism_optimization[]`.

The deterministic script **validates structure and copies** these entries to the output; it does not score similarity or rewrite text.

## When to Add an Entry

Add a `plagiarism_optimization` item when you observe:

| Signal | Typical `risk` value |
|--------|----------------------|
| Same long phrase appears in multiple sections | `cross_section_repetition` |
| Wording closely mirrors a well-known survey or template | `common_template_wording` |
| Phrase likely overlaps published literature without citation | `high_similarity_phrase` |
| Other heuristic concern | `other` |

Also cross-check [`academic-tone-zh.md`](academic-tone-zh.md): deduplicate repetitive spans in the body **and** log the edit in `polish_log` when you rewrite.

## Entry Template

Each item **must** include `location`, `risk`, and `suggestion`. Include `original` and `rewrite_hint` when they help the author revise.

```json
{
  "location": "相关工作",
  "risk": "high_similarity_phrase",
  "original": "大语言模型驱动的智能体正在重塑知识工作者的创作流程",
  "suggestion": "改写为差异化表述并补充本文 LangGraph + Skill 双轨架构对比维度",
  "rewrite_hint": "突出编排层状态图与 OpenClaw Skill 热插拔机制的差异"
}
```

### Field Semantics

| Field | Required | Description |
|-------|----------|-------------|
| `location` | Yes | Section title or paragraph anchor (e.g. `引言`, `相关工作`, `摘要第二段`) |
| `risk` | Yes | One of `high_similarity_phrase`, `cross_section_repetition`, `common_template_wording`, `other` |
| `original` | Recommended | The problematic or repetitive source phrase (truncate with `…` if long) |
| `suggestion` | Yes | What to change and why — direction, not full replacement prose |
| `rewrite_hint` | Recommended | Paper-specific angle: architecture, dataset, evaluation metric, etc. |

## Rewrite Principles

1. **Preserve facts and citations** — see [`citation-preservation.md`](citation-preservation.md); rephrase around `[n]`, never drop markers.
2. **Differentiate by contribution** — emphasize what *this* paper adds (method, system design, empirical setting).
3. **Avoid synonym-only swaps** — replace template structure, not just adjectives (`显著` ↔ `明显`).
4. **One issue per entry** — split multi-location problems into separate items with distinct `location` values.
5. **Empty array is valid** — use `[]` when no similarity concerns remain after polish.

## Relationship to `polish_log`

| Artifact | Purpose |
|----------|---------|
| `polish_log[]` | Changes **already applied** by the Agent during this pass |
| `plagiarism_optimization[]` | Residual risks or follow-up rewrite **suggestions** for the author |

If you fully resolved a repetitive span, log it in `polish_log` with `change_type: deduplication`. Only keep a `plagiarism_optimization` entry when further human review or a later pass may be needed.

## Agent Checklist

1. Scan formatted draft for cross-section boilerplate (especially opening paragraphs copied across chapters).
2. After polishing, list remaining high-risk phrases in `plagiarism_optimization[]`.
3. Ensure each entry has concrete `suggestion` and, where possible, `rewrite_hint` tied to this paper's contributions.
4. Do not fabricate similarity percentages or vendor report IDs — this stage records qualitative guidance only.

## Script Behavior

- Input entries are copied to `polished_draft.plagiarism_optimization` on success.
- Schema validation (future `validate.py`) checks required fields per [`input.schema.json`](../contracts/input.schema.json).
- Entries do **not** affect `quality_checks.tone_academic` directly; unresolved body repetition may still trigger `repetitive_phrasing` warnings from diff/heuristic checks.
