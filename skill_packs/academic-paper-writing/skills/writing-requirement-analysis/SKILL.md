---
name: writing-requirement-analysis
description: 将模糊写作意图结构化为 writing_task 契约和论文写作任务书。Use when requirement_analysis stage, or user mentions 选题定位, 任务书, 论证规划, 论文类型, 期刊约束, contribution, writing_task. 中文优先，不编造期刊、数据或结论。
---

# Writing Requirement Analysis

## Scope

Use this skill only for workflow stage `requirement_analysis`.

The deliverables are:

- `writing_task`: machine-readable JSON contract for downstream literature review, outline, drafting, formatting, and polishing.
- `task_book_markdown`: human-readable 论文写作任务书 rendered from the same contract.

Do not write paper body prose, summarize references, or allocate per-chapter word budgets here. Chapter-level word budgets belong to the `paper_outline` stage.

## Domain Goal

Turn unclear writing intent into an explicit writing contract:

- Identify topic, paper type, language, target journal or venue class, and total word limit.
- Clarify core claim, core arguments, contribution list, research scope, and out-of-scope boundary.
- Match target venue style using `references/contracts/journal/ccf-b-profiles.yaml` when possible.
- Record reference seed material for the literature stage.
- Surface missing critical information before the script runs.

## Evidence Principles

- Default to Chinese academic expression. Preserve English paper titles, model names, formulas, variables, commands, and reference entries.
- Do not invent journal rules, DOI values, experiment data, paper claims, or user intent.
- Mark information as `原文/已有数据`, `用户确认`, `推断`, or `建议` in `provenance`.
- Critical writing-task fields must be `原文/已有数据` or `用户确认`.
- Use `推断` only for reversible interpretation and summarize it explicitly.

## Critical Fields

Confirm these before running the script:

- `argument_brief.topic`
- `argument_brief.core_claim`
- `argument_brief.core_arguments[]`
- `argument_brief.contributions[]`
- `argument_brief.venue.paper_type`
- `argument_brief.venue.journal` or `argument_brief.venue.level`
- `argument_brief.venue.word_limit` as total paper length
- `argument_brief.venue.language`
- `argument_brief.scope.boundary`
- `references_seed[]`

Do not ask for chapter-level word budgets in this stage. Set `word_limit.by_chapter` to `null`; the script records `chapter_allocation_stage = "paper_outline"`.

## Input Contract

The Agent prepares a completed `argument_brief`, not raw notes:

```json
{
  "user_request": "审计用原始文本",
  "argument_brief": {
    "topic": "论文题目或主题",
    "problem": {"actor": "...", "failure_mode": "...", "root_cause": "..."},
    "gap": {"prior_assumptions": ["..."], "type": "structural"},
    "core_claim": "本文表明...",
    "contribution_name": "2-4 词核心概念名",
    "core_arguments": ["核心论点 1"],
    "contributions": ["贡献 1"],
    "venue": {"paper_type": "system", "journal": "计算机研究与发展", "level": "CCF-B", "word_limit": 10000, "language": "zh"},
    "scope": {"domain": "...", "subtopics": ["..."], "boundary": "..."},
    "section_plan": [{"chapter_id": "1", "title": "引言", "key_points": ["..."], "depends_on": null}],
    "narrative_spine": "...",
    "evidence_plan": []
  },
  "references_seed": [{"id": "seed-bib", "type": "bibtex", "path": "case/references/seed.bib"}],
  "provenance": {"core_claim": "用户确认", "word_limit": "用户确认"}
}
```

## Output Contract

The script writes:

```json
{
  "artifact_type": "writing_task",
  "writing_task": {
    "topic": "...",
    "paper_type": "system",
    "language": "zh",
    "target_journal": {"name": "...", "level": "...", "style_profile": {}},
    "word_limit": {"total": 10000, "by_chapter": null, "chapter_allocation_stage": "paper_outline"},
    "core_arguments": ["..."],
    "innovation_points": ["..."],
    "research_scope": {"domain": "...", "subtopics": [], "boundary": "..."},
    "chapter_framework": [{"chapter_id": "1", "title": "引言", "key_points": [], "word_budget": null, "depends_on": null}],
    "references_seed": [],
    "missing_info": []
  },
  "task_book_markdown": "# 论文写作任务书 ...",
  "task_book_markdown_path": "path/to/output.md",
  "quality_checks": {
    "required_fields_confirmed": true,
    "journal_profile_matched": true,
    "task_book_rendered": true
  }
}
```

## Final Checks

- The topic, paper type, target venue or venue class, language, and total word limit are explicit.
- Each core argument is user-confirmed or clearly derived from confirmed context.
- Scope boundaries say what the paper will not cover.
- `missing_info` is empty on successful output.
- Per-chapter `word_budget` is `null`; `paper_outline` allocates it later.
- The script did not infer meaning from raw prose.
