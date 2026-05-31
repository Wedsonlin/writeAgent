---
name: paper-content-generation
description: 分章节内容生成 Skill。当 state.outline 已生成、state.draft 仍为空时触发；或用户提到"生成正文/分章节撰写/写初稿"时触发。按大纲逐章节产出学术化正文（含摘要、引言、方法、实验、讨论、结论），自动嵌入引用标号，控制各章节字数。
user-invocable: true
disable-model-invocation: false
homepage: https://example.org/writeagent
metadata: {"openclaw":{"requires":{"bins":["python"],"env":["WRITEAGENT_LLM_API_KEY"]},"primaryEnv":"WRITEAGENT_LLM_API_KEY"}}
---

# 分章节内容生成 Skill（接口骨架）

> 本文件作为接口契约。

## 何时使用

- `state.outline` 就绪、`state.draft` 缺失。
- 用户显式要求"生成正文 / 写初稿"。

## 调用方式

```bash
python {baseDir}/scripts/run.py --state {workspace}/state.json \
    [--start-section <id>] [--end-section <id>]
```

可选参数允许只生成指定区间的章节，便于增量撰写与重写。

## 输入

- `state.outline`（`schemas/paper_outline.schema.json`）
- `state.literature_report`（用于引用与论据支撑）
- `state.writing_task`（用于语言、字数、风格控制）

## 输出

- `state.draft`（**严格符合** `schemas/paper_draft.schema.json`）
- `outputs/04-论文分章节初稿.md`

### 必须填充的字段

- `abstract`：摘要 200-400 字
- `keywords`：5-8 个
- `sections[]`：每节包含
  - `id`（对应 `paper_outline.sections.id`）
  - `title`
  - `content_markdown` —— 正文 Markdown，引用以 `[n]` 形式嵌入
  - `citations_used[]` —— 用到的文献 id
  - `word_count` —— 实际字数

## 与上下游契约

- **必须保留** `outline.sections.id` 的顺序与编号。
- 引用 id 必须出现在 `literature_report.papers.id` 中。
- 摘要单独存放，不重复到 `sections[]`。

## 撰写要求

- 语言学术化，避免口语化表达。
- 每节字数偏差 ≤ ±15%。
- 关键论点必须有引用支撑；同一观点引用 ≤ 3 处。

## 异常情况

- LLM 单节生成失败：重试 1 次；仍失败则把该节 `content_markdown` 标记为 `<!-- TODO -->`，并加入 `open_questions`。
- 章节字数超限：自动启动压缩 pass（保留要点，删除冗余）。

## TODO（组员 2 完成）

- [ ] `scripts/run.py`
- [ ] `scripts/prompts.py` 按章节类型（引言/方法/实验...）分别定制
- [ ] `scripts/citation_inject.py` 把 `paper_id` 替换为 `[n]` 并维护编号表
- [ ] `scripts/section_writer.py` 单节生成逻辑（含字数控制）
- [ ] `references/` 各类型章节示例
