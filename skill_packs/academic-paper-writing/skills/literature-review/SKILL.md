---
name: literature-review
description: 基于 writing_task 构建逐篇 Source Map 与主题式 research landscape，经脚本生成 literature_report，含 GB/T 7714 与 APA 书目。Use when literature_review stage, writing_task exists, or user mentions 文献梳理, 引用, related work, bibliography, BibTeX. 按主题组织而非逐篇流水账；不编造 DOI 或文献结论。
metadata: {"openclaw":{"requires":{"bins":["python"]}}}
---

# Literature Review

## Scope

Use this skill only after a `writing_task` artifact exists. The deliverable is a `literature_report` JSON artifact that supports outline and drafting.

Do not use this skill to invent references, write the full related-work prose, or decide the paper's topic. Those belong to upstream requirement analysis or downstream drafting.

## Evidence Principles

- Default to Chinese synthesis while preserving English paper titles, venues, model names, DOI, URL, and reference entries.
- Do not invent DOI, authors, venues, experimental numbers, page ranges, or claims not present in the available source material.
- Distinguish original source statements from Agent inference in `source_map[].provenance`.
- Organize related work by theme, assumption, method, or gap. Avoid paper-by-paper chronology unless the timeline itself is the argument.

## Workflow

1. Inspect progress and confirm `writing_task` exists.
2. Read the `writing_task`, especially `topic`, `core_arguments`, `research_scope.subtopics`, `target_journal.style_profile.citation_style`, and `references_seed`.
3. Parse available references mentally or through safe file reads. For each paper, prepare a `source_map` entry using `references/source-map/per-paper-template.md`.
4. Read `references/synthesis/related-work-by-theme.md` and group papers into a theme-first `landscape`.
5. Align each paper to `writing_task.core_arguments[]` using stance values: `supports`, `extends`, `contradicts`, or `background`.
6. Prepare an input JSON matching `references/contracts/input.schema.json`.
7. Run the deterministic script:

```text
python skill_packs/academic-paper-writing/skills/literature-review/scripts/run.py --input path/to/input.json --output path/to/output.json
```

8. Record the output with `update_artifact_manifest`, advance `literature_review` with `update_progress`, and summarize unmapped papers or low-confidence claims.

## Input Contract

The Agent prepares:

```json
{
  "writing_task": {"...": "上游 artifact"},
  "citation_style": "GB/T 7714",
  "source_map": [
    {
      "paper_id": "yao2022react",
      "research_question": "...",
      "core_method": "...",
      "main_finding": "...",
      "key_claims": ["..."],
      "evidence_strength": "moderate",
      "limitations": [],
      "alignment_to_core": [{"core_argument_index": 0, "stance": "supports", "note": "..."}],
      "provenance": {"main_finding": "原文 abstract"}
    }
  ],
  "landscape": {
    "keywords": ["..."],
    "clusters": [{"name": "...", "summary": "...", "paper_ids": ["..."]}],
    "consensus": ["..."],
    "controversies": ["..."],
    "research_gaps": ["..."],
    "timeline_summary": "..."
  },
  "extra_references": []
}
```

## Output Contract

The script writes:

```json
{
  "artifact_type": "literature_report",
  "literature_report": {
    "keywords": [],
    "papers": [],
    "research_landscape": {"clusters": [], "timeline_summary": "..."},
    "consensus": [],
    "controversies": [],
    "research_gaps": [],
    "citation_style": "GB/T 7714",
    "formatted_bibliography": {"gb7714": [], "apa": []}
  }
}
```

## Final Checks

- Every parsed BibTeX paper appears in `papers[]`.
- Missing Source Map entries are reported under `unmapped_papers`, not silently dropped.
- Cluster `paper_ids` all exist.
- Alignment indexes refer to real `writing_task.core_arguments[]`.
- Bibliography arrays have the same length as `papers[]`.
