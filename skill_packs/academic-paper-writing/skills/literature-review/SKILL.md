---
name: literature-review
description: 基于论文写作任务书 Markdown、writing_task JSON anchors、参考文献清单和研究方向关键词，检索并补充相关论文，提取核心观点，梳理研究领域脉络，生成中文 JSON 与 Markdown 双版本 literature_report 文献梳理报告，报告内含 GB/T 7714/APA 参考文献。Use when literature_review stage, task_book_markdown, writing_task, research keywords, references_seed, 文献梳理, related work, bibliography, BibTeX, PDF references. 按主题组织而非逐篇流水账；不编造 DOI 或文献结论。
---

# Literature Review

## Scope

Use this skill after the requirement-analysis stage has produced a paper writing task book. The deliverable is a Chinese literature mapping report with a machine-readable `literature_report` JSON version and a human-readable Markdown version.

Do not use this skill to invent references, write the full related-work prose, or decide the paper's topic. Those belong to upstream requirement analysis or downstream drafting.

## Input Policy

Treat `task_book_markdown` or `task_book_markdown_path` as the primary semantic source for the paper writing task book.

Use `writing_task` only as stable machine-readable anchors:

- `topic`
- `core_arguments`
- `innovation_points`
- `research_scope.domain`
- `research_scope.subtopics`
- `research_scope.boundary`
- `references_seed`
- `task_book_sections.argument_evidence_matrix`
- `task_book_sections.downstream_constraints`
- `target_journal.style_profile.citation_style`

Use explicit `research_keywords` first. If they are absent, derive keywords from the task book Markdown and the JSON anchors above. If Markdown and JSON conflict, prefer user-confirmed task-book wording and record the conflict in the report summary or provenance.

## Evidence Principles

- Express report-facing synthesis in Chinese. Preserve native English only for paper titles, author names, venue names, tool/model/system names, acronyms, DOI, URL, citation keys, and established technical terms.
- When evidence comes from English abstracts or papers, synthesize Chinese `source_map` values instead of copying the English abstract into `main_finding` or `key_claims`.
- Prefer localized fields when available: `abstract_zh`, `main_finding_zh`, `key_claims_zh`, `limitations_zh`, `name_zh`, `summary_zh`, `consensus_zh`, `controversies_zh`, `research_gaps_zh`, and `timeline_summary_zh`.
- Treat `paper_reading_cards[]` as the primary evidence carrier. A naked `source_map[]` entry without `source_urls` and `source_artifact_ids` is weak/unmapped evidence.
- Do not invent DOI, authors, venues, experimental numbers, page ranges, or claims not present in the available source material.
- Distinguish original source statements from Agent inference in `source_map[].provenance`.
- Organize related work by theme, assumption, method, or gap. Avoid paper-by-paper chronology unless the timeline itself is the argument.

## Workflow

1. Read the task book Markdown and JSON anchors. Extract topic, core arguments, innovation points, scope boundaries, target citation style, reference seeds, and `argument_evidence_matrix`.
2. Parse `references_seed` into paper batches of 3-5 papers. For each batch, call the configured `literature-paper-reader-agent` through the `task` tool and request `paper_reading_cards[]` only.
3. For each paper reader result, verify that moderate/strong support has `source_urls` and `source_artifact_ids`. If not, downgrade it to weak and mark the gap.
4. Build `source_map[]` from `paper_reading_cards[]` using `references/source-map/per-paper-template.md` and `references/source-map/evidence-labels.md`.
5. Build `argument_support_matrix[]` and `innovation_support_matrix[]`. Each core argument and innovation point must either list supporting papers or explicitly state a gap.
6. Read `references/coverage-rubric.md`. Decide whether seed references cover the task book, keywords, core arguments, and innovation points.
7. If coverage is insufficient, read `references/search-strategy.md`, generate targeted queries from uncovered arguments/innovations, call `search_knowledge` with `intent="academic_papers"`, then call `extract_sources` for selected URLs before using claims. Store the result in `supplement_search_summary`.
8. Read `references/synthesis/related-work-by-theme.md` and `references/synthesis/landscape-checklist.md`. Build a theme-first `landscape` with research status, field clusters, consensus, controversies, gaps, and a timeline when useful.
9. Prepare an input JSON matching `references/contracts/input.schema.json`.
10. Run the deterministic script:

```text
python skill_packs/academic-paper-writing/skills/literature-review/scripts/run.py --input path/to/input.json --output path/to/output.json
```

11. Summarize task alignment, research status, field landscape, core paper viewpoints, argument/innovation support, research gaps, supplementary search status, unmapped papers, and bibliography status. Do not create a separate bibliography artifact; references belong inside the report.

## Input Contract

The Agent prepares:

```json
{
  "task_book_markdown": "# 论文写作任务书 ...",
  "task_book_markdown_path": "optional/path/to/task-book.md",
  "writing_task": {"...": "JSON anchors from upstream artifact"},
  "research_keywords": ["智能体", "学术写作", "工具调用"],
  "citation_style": "GB/T 7714",
  "paper_reading_cards": [
    {
      "paper_id": "yao2022react",
      "source_urls": ["https://..."],
      "source_artifact_ids": ["extract-..."],
      "reading_status": "read",
      "research_problem_zh": "...",
      "method_zh": "...",
      "main_claims_zh": ["具体、非模板化的中文观点"],
      "evidence_zh": ["..."],
      "limitations_zh": [],
      "relevance_to_arguments": [{"core_argument_index": 0, "stance": "supports", "support_strength": "moderate", "evidence_summary_zh": "..."}],
      "relevance_to_innovations": [{"innovation_index": 0, "stance": "background", "support_strength": "moderate", "evidence_summary_zh": "..."}]
    }
  ],
  "source_map": [
    {
      "paper_id": "yao2022react",
      "research_question": "...",
      "core_method": "...",
      "main_finding": "...",
      "abstract_zh": "...",
      "main_finding_zh": "...",
      "key_claims": ["..."],
      "key_claims_zh": ["..."],
      "evidence_strength": "moderate",
      "limitations": [],
      "limitations_zh": [],
      "alignment_to_core": [{"core_argument_index": 0, "stance": "supports", "note": "..."}],
      "source_urls": ["https://..."],
      "source_artifact_ids": ["extract-..."],
      "provenance": {"main_finding": "extract_sources"}
    }
  ],
  "argument_support_matrix": [],
  "innovation_support_matrix": [],
  "landscape": {
    "keywords": ["..."],
    "clusters": [{"name": "...", "name_zh": "...", "summary": "...", "summary_zh": "...", "paper_ids": ["..."]}],
    "consensus": ["..."],
    "consensus_zh": ["..."],
    "controversies": ["..."],
    "controversies_zh": ["..."],
    "research_gaps": ["..."],
    "research_gaps_zh": ["..."],
    "timeline_summary": "...",
    "timeline_summary_zh": "..."
  },
  "supplement_search_summary": {"status": "not_required"},
  "extra_references": [
    {
      "type": "paper",
      "id": "supplement2024",
      "title": "...",
      "authors": ["..."],
      "year": 2024,
      "venue": "...",
      "doi": null,
      "url": "...",
      "abstract": "...",
      "source_kind": "search_evidence"
    }
  ]
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
    "paper_reading_cards": [],
    "task_alignment": {},
    "argument_support_matrix": [],
    "innovation_support_matrix": [],
    "research_landscape": {"clusters": [], "timeline_summary": "..."},
    "consensus": [],
    "controversies": [],
    "research_gaps": [],
    "supplement_search_summary": {},
    "citation_style": "GB/T 7714",
    "formatted_bibliography": {"gb7714": [], "apa": []},
    "report_sections": {
      "task_alignment": {},
      "research_status": [],
      "field_context": {"clusters": [], "timeline_summary": "..."},
      "core_literature_viewpoints": [],
      "argument_support_matrix": [],
      "innovation_support_matrix": [],
      "research_gaps": [],
      "supplement_search_summary": {},
      "references": {"gb7714": [], "apa": []}
    },
    "unmapped_papers": []
  },
  "literature_report_markdown": "# 文献梳理报告 ...",
  "literature_report_markdown_path": "path/to/output.md"
}
```

The JSON and Markdown reports must both cover:

- 研究现状
- 领域脉络
- 核心文献观点
- 论点与创新点支撑矩阵
- 研究缺口与补充检索
- 规范参考文献列表

GB/T 7714 and APA references are part of the report, not a separate output artifact.

Both outputs must use Chinese for generated explanations and synthesis, while preserving native English for paper titles, author names, venues, technical terms, DOI, URLs, and citation keys.

## Final Checks

- Every parsed BibTeX paper appears in `papers[]`.
- Missing Source Map entries are reported under `unmapped_papers`, not silently dropped or treated as verified evidence.
- Every moderate/strong core claim comes from `paper_reading_cards[]` with source URLs and evidence artifacts.
- Every core argument and innovation point appears in the support matrices.
- Cluster `paper_ids` all exist.
- Alignment indexes refer to real `writing_task.core_arguments[]`.
- Bibliography arrays have the same length as `papers[]`.
- Claims from search snippets are not used unless confirmed through extraction or reliable metadata.
