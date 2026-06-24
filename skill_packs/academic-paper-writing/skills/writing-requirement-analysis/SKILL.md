---
name: writing-requirement-analysis
description: Use when writeAgent is in requirement_analysis, structuring vague academic-paper requests into writing_task, asking for missing target journal/conference, paper type, word limit, scope, and reference seed before downstream writing.
---

# Writing Requirement Analysis

## Scope

Use this skill only for workflow stage `requirement_analysis`.

The deliverables are:

- `writing_task`: machine-readable JSON contract for downstream literature review, outline, drafting, formatting, and polishing.
- `writing_task.task_book_sections`: machine-readable structured sections for confirmation sources, downstream constraints, argument-evidence needs, and target venue format points.
- `task_book_markdown`: human-readable 论文写作任务书 rendered from the same contract.

Do not write paper body prose, summarize references, or allocate per-chapter word budgets here. Confirm only the total paper length; chapter-level word budgets belong to the `paper_outline` stage.

## Domain Goal

Turn unclear writing intent into an explicit writing contract:

- Identify topic, paper type, language, explicit target journal/conference name, and total word limit.
- Clarify core claim, core arguments, contribution list, research scope, and out-of-scope boundary.
- Match target venue style using `references/contracts/journal/ccf-b-profiles.yaml` when possible.
- Record reference seed material for the literature stage.
- Ask the user to complete missing critical information before the script runs.

## Venue Contract

Skill1 accepts only one target-venue state: the user has confirmed a concrete journal or conference name.

Accepted fields under `argument_brief.venue`:

- `journal`: concrete journal name.
- `conference`: concrete conference name.
- `name`: concrete venue name when the type is not important.
- `level`: optional short label such as `CCF-B`, `中文核心`, or `课程论文目标`; do not put provenance or assumptions here.

The script normalizes these fields to `writing_task.target_journal.name` in priority order: `journal -> conference -> name`. The field name stays `target_journal` for downstream compatibility, but its `name` may hold either a journal or a conference.

The following are not valid target venues and require `ask_user` before running the script:

- `待定`, `未定`, `未锁定`, or similar placeholders.
- `参考《某期刊》风格`, `参考某会议格式`, or any style-only reference.
- `中文计算机类综述论文层级`, `CCF-B 层级`, `课程论文目标`, or any venue class without a concrete name.

## Paper Type Contract

`argument_brief.venue.paper_type` must resolve to exactly one of:

- `survey`: 中文“综述” or “综述类论文”.
- `research`: 中文“研究型论文”.

Do not use `system`, `empirical`, `theoretical`, or other subtypes in Skill1 output. If the user’s intent is ambiguous, call `ask_user` and ask them to choose “综述” or “研究型论文”. Method, experiment, system, or theory details are refined by later stages.

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
- `argument_brief.venue.journal`, `argument_brief.venue.conference`, or `argument_brief.venue.name` with a concrete target name
- `argument_brief.venue.word_limit` as total paper length
- `argument_brief.venue.language`
- `argument_brief.scope.boundary`
- `references_seed[]`

Do not ask for chapter-level word budgets in this stage. Set `word_limit.by_chapter` to `null`; the script records `chapter_allocation_stage = "paper_outline"`.

## Input Contract

The Agent prepares a completed `argument_brief`, not raw notes:

```json
{
  "user_request": "用户原始写作需求",
  "argument_brief": {
    "topic": "论文题目或主题",
    "problem": {"actor": "...", "failure_mode": "...", "root_cause": "..."},
    "gap": {"prior_assumptions": ["..."], "type": "structural"},
    "core_claim": "本文表明...",
    "contribution_name": "2-4 词核心概念名",
    "core_arguments": ["核心论点 1"],
    "contributions": ["贡献 1"],
    "venue": {
      "paper_type": "综述",
      "journal": "计算机研究与发展",
      "level": "CCF-B",
      "word_limit": 10000,
      "language": "zh"
    },
    "scope": {"domain": "...", "subtopics": ["..."], "boundary": "..."},
    "section_plan": [{"chapter_id": "1", "title": "引言", "key_points": ["..."], "depends_on": null}],
    "narrative_spine": "...",
    "evidence_plan": []
  },
  "references_seed": [{"id": "seed-bib", "type": "bibtex", "path": "case/references/seed.bib"}],
  "provenance": {"core_claim": "用户确认", "word_limit": "用户确认", "target_venue": "用户确认"}
}
```

## Output Contract

The script writes:

```json
{
  "artifact_type": "writing_task",
  "writing_task": {
    "topic": "...",
    "paper_type": "survey",
    "language": "zh",
    "target_journal": {"name": "计算机研究与发展", "level": "CCF-B", "style_profile": {}},
    "word_limit": {"total": 10000, "by_chapter": null, "chapter_allocation_stage": "paper_outline"},
    "core_arguments": ["..."],
    "innovation_points": ["..."],
    "research_scope": {"domain": "...", "subtopics": [], "boundary": "..."},
    "chapter_framework": [{"chapter_id": "1", "title": "引言", "key_points": [], "word_budget": null, "depends_on": null}],
    "references_seed": [],
    "task_book_sections": {
      "confirmation_sources_and_assumptions": {
        "confirmed_sources": [{"field": "target_venue", "source": "用户确认"}],
        "assumptions": ["总字数已在需求分析阶段确认，章节字数分配由 paper_outline 阶段完成。"]
      },
      "downstream_constraints": [{"stage": "literature_review", "constraint": "..."}],
      "argument_evidence_matrix": [{"argument": "...", "evidence_needs": ["..."]}],
      "target_venue_format_points": {
        "target_name": "计算机研究与发展",
        "level": "CCF-B",
        "citation_style": "GB/T 7714",
        "tone": "formal-zh",
        "structure_hint": "摘要(中英)-引言-相关工作-方法-实验-讨论-结论-参考文献"
      }
    },
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

- Topic, paper type, concrete target journal/conference name, language, and total word limit are explicit.
- `paper_type` is only `survey` or `research`.
- Target venue is not a style reference, level, class, or placeholder.
- Each core argument is user-confirmed or clearly derived from confirmed context.
- Scope boundaries say what the paper will not cover.
- `writing_task.task_book_sections` includes machine-readable “确认来源与假设”, “后续阶段约束”, “核心论点-证据需求矩阵”, and “目标期刊/会议格式要点”.
- `task_book_markdown` renders those same `task_book_sections` for human review.
- `missing_info` is empty on successful output.
- Per-chapter `word_budget` is `null`; `paper_outline` allocates it later.
- The script did not infer meaning from raw prose.
