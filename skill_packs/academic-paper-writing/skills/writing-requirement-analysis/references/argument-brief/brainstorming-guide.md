# Argument Brief Brainstorming Guide

Source note: adapted from the MIT-licensed `research-writing-skill` brainstorming guide in `zLanqing/codex-claude-academic-skills`, rewritten for writeAgent's JSON artifact workflow.

Use this guide before running the script. The goal is not to write prose; it is to produce an `argument_brief` precise enough for downstream skills.

## Phase 1: Problem Discovery

Answer these questions in concrete terms:

- Who is affected by the problem? Name a specific actor, not a vague "user".
- What breaks today? Describe the observable failure mode.
- Why does it break? Identify the structural limitation, missing abstraction, or workflow mismatch.
- What happens if nobody solves it? State the academic, engineering, or teaching cost.

Write the result into:

- `problem.actor`
- `problem.failure_mode`
- `problem.root_cause`

## Phase 2: Gap Positioning

Clarify why the topic is worth a paper:

- What assumptions do existing methods or systems make?
- Which assumptions fail in this setting?
- Is the gap structural, quantitative, methodological, or pedagogical?

Write the result into:

- `gap.prior_assumptions[]`
- `gap.type`

## Phase 3: Core Claim

Complete this sentence: `本文表明...`

Then name the core idea in two to four words. The name should be a reusable concept, not a slogan.

Write the result into:

- `core_claim`
- `contribution_name`
- `contributions[]`
- `core_arguments[]` when the claims differ from contribution wording

## Phase 4: Venue And Form

Identify:

- Paper type: `system`, `survey`, `empirical`, or `theoretical`.
- Target journal, conference, thesis, or course-report style.
- Language and word limit.
- Citation style if known.

Write the result into `venue`.

## Phase 5: Research Scope

Separate what the paper covers from what it does not cover.

Write:

- `scope.domain`
- `scope.subtopics[]`
- `scope.boundary`

## Phase 6: Section Architecture

Draft the section plan only after the core claim and venue are clear.

Each section needs:

- `chapter_id`
- `title`
- `key_points[]`
- `word_budget`
- `depends_on` when it depends on upstream evidence

If exact budgets are unknown, use a reasonable total-level allocation and record `word_limit.by_chapter` as unresolved.

## Phase 7: Evidence Plan

For each contribution, record the expected evidence type:

- literature support
- system architecture
- case study
- experiment or benchmark
- user or workflow observation

Write optional entries into `evidence_plan[]`.

## Phase 8: Narrative Spine

Summarize the paper in three or four sentences:

1. The world has problem X.
2. Existing approaches fail because Y.
3. This paper introduces or shows Z.
4. The result enables W within the stated boundary.

Write the result into `narrative_spine`.
