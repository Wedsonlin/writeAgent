# Related Work By Theme

Source note: adapted from the related-work guidance in `zLanqing/codex-claude-academic-skills/research-writing-skill`.

A literature review for writeAgent should be theme-first, not paper-by-paper.

## Good Cluster Axes

- Agent architecture and tool use
- Skill/plugin capability packaging
- Academic writing assistance
- Evaluation, prompting, retrieval, or other supporting techniques

## Cluster Requirements

Each cluster needs:

- `name`: a compact theme label.
- `summary`: what this theme contributes to the user's topic.
- `paper_ids[]`: BibTeX keys from parsed references.

## Synthesis Requirements

Write:

- `consensus[]`: what the literature broadly agrees on.
- `controversies[]`: unresolved design choices or competing assumptions.
- `research_gaps[]`: gaps aligned with the user's `writing_task.core_arguments`.
- `timeline_summary`: short chronology only when it helps explain the field.

Avoid:

- One paragraph per paper without comparison.
- Claims unsupported by source maps.
- Treating documentation, preprints, and peer-reviewed studies as equal evidence without noting strength.
