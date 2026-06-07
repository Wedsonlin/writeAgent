---
name: writing-requirement-analysis
description: 将模糊写作意图经论证简报 argument brief 结构化为 writing_task 契约。Use when requirement_analysis stage, or user mentions 选题定位, 任务书, 论证规划, 论文类型, 期刊约束, contribution, writing_task. 中文优先，不编造期刊、数据或结论。
metadata: {"openclaw":{"requires":{"bins":["python"]}}}
---

# Writing Requirement Analysis

## Scope

Use this skill only for workflow stage `requirement_analysis`. The deliverable is a `writing_task` JSON artifact that downstream outline, drafting, formatting, and polishing skills can consume without reading the conversation history.

Do not use this skill to write the paper body, summarize references, or create an outline from literature evidence. Use `literature-review` after `writing_task` exists.

## Evidence Principles

- Default to Chinese academic expression. Preserve English paper titles, model names, formulas, variables, commands, and reference entries.
- Do not invent journal rules, DOI values, experiment data, paper claims, or user intent.
- Mark information as `原文/已有数据`, `用户确认`, `推断`, or `建议` when preparing the input contract.
- Treat the script as a final contract gate. The Agent must do the reasoning before the script runs.

## Workflow

1. Inspect progress and confirm this stage is not already complete.
2. Read `references/argument-brief/brainstorming-guide.md` and build an `argument_brief` from the user's writing intent.
3. If any critical field is missing, call `ask_user` with `missing_fields` and wait. Critical fields are: core claim, contribution list, paper type, target venue or venue class, language, and expected length.
4. Read `references/argument-brief/paper-type-guide.md` when the paper type or section architecture is unclear.
5. Read `references/argument-brief/evidence-labels.md` before filling `provenance`.
6. Prepare an input JSON matching `references/contracts/input.schema.json`. The script should receive a completed `argument_brief`, not raw unstructured notes.
7. Run the deterministic script:

```text
python skill_packs/academic-paper-writing/skills/writing-requirement-analysis/scripts/run.py --input path/to/input.json --output path/to/output.json
```

8. Record the output with `update_artifact_manifest`, advance `requirement_analysis` with `update_progress`, and summarize remaining assumptions.

## Input Contract

The Agent prepares:

```json
{
  "user_request": "审计用原始文本",
  "argument_brief": {
    "topic": "论文题目或主题",
    "problem": {"actor": "...", "failure_mode": "...", "root_cause": "..."},
    "gap": {"prior_assumptions": ["..."], "type": "structural"},
    "core_claim": "本文表明...",
    "contribution_name": "2-4 词核心概念名",
    "contributions": ["...", "..."],
    "venue": {"paper_type": "system", "journal": "计算机研究与发展", "level": "CCF-B", "word_limit": 10000, "language": "zh"},
    "scope": {"domain": "...", "subtopics": ["..."], "boundary": "..."},
    "section_plan": [{"chapter_id": "1", "title": "引言", "key_points": ["..."], "word_budget": 800}],
    "narrative_spine": "...",
    "evidence_plan": []
  },
  "references_seed": [{"id": "seed-bib", "type": "bibtex", "path": "case/references/seed.bib"}],
  "provenance": {"core_claim": "用户确认", "word_limit": "原文/已有数据"}
}
```

## Output Contract

The script writes:

```json
{
  "artifact_type": "writing_task",
  "writing_task": {
    "topic": "...",
    "paper_type": "...",
    "language": "zh",
    "target_journal": {"name": "...", "level": "...", "style_profile": {}},
    "word_limit": {"total": 10000, "by_chapter": null},
    "core_arguments": ["..."],
    "innovation_points": ["..."],
    "research_scope": {"domain": "...", "subtopics": [], "boundary": "..."},
    "chapter_framework": [],
    "references_seed": [],
    "missing_info": []
  }
}
```

## Final Checks

Before reporting completion, verify:

- The topic, paper type, target venue, language, and word limit are explicit.
- Each core argument is user-confirmed or clearly derived from confirmed context.
- Scope boundaries say what the paper will not cover.
- Chapter budgets are present or `missing_info` records who should allocate them later.
- The script did not infer meaning from raw prose.
