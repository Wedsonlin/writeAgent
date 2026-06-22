# Heading Rules

Deterministic heading normalization for Chinese journal-style Markdown output.

## Rendered Markdown Structure

| Block | Markdown heading | Notes |
|-------|------------------|-------|
| Paper title | `# {title}` | Exactly one top-level heading |
| Abstract | `## 摘要` | Fixed label; not taken from `sections[]` |
| Keywords | Plain line `**关键词**：…` | No heading |
| Body sections | `##` … `######` | Derived from `sections[].level` |
| References | `## 参考文献` | Fixed label; not taken from `sections[]` |

Default `abstract_heading` in `formatting_constraints.heading_rules` is `## 摘要`.

## `sections[].level` Semantics

- `level` is a logical nesting depth starting at `1` for top-level chapters (引言, 相关工作, …).
- `level: 2` denotes a subsection (e.g. 核心模块 under 系统设计).
- The script maps `level` to Markdown hashes as `level + 1` (level 1 → `##`, level 2 → `###`, level 3 → `####`).
- `formatting_constraints.heading_rules.max_level` caps nesting (default `3`).

## No Level Jumps

Heading levels must be **continuous** in document order:

- Valid: `1 → 1 → 2 → 1`
- Invalid: `1 → 3` (skips level 2)
- Invalid: `1 → 2 → 4` (skips level 3)

When a jump is detected, the script records `heading_level_jump` in `issues[]` and remaps levels to the nearest valid sequence (e.g. `1 → 3` becomes `1 → 2`).

## Agent Responsibilities

- Keep section titles non-empty; empty titles are skipped in rendering and reported as `missing_section_title`.
- Do not embed Markdown heading markers (`#`, `##`) inside `content_markdown`; headings come only from `sections[].title` and `level`.
- Do not add 摘要 or 参考文献 as regular `sections[]` entries; those blocks are rendered from `abstract` and `references`.

## Quality Check

`quality_checks.headings_normalized` is `true` when no unresolved `heading_level_jump` or `missing_section_title` warnings remain after normalization.
