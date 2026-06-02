---
name: paper-outline
description: 论文大纲与章节框架设计 Skill。当 state.writing_task 与 state.literature_report 已生成、state.outline 仍为空时触发；或用户提到"大纲/章节框架/outline/结构调整"时触发。输出含一级/二级/三级标题、每节核心要点、逻辑衔接说明、字数分配与引用文献映射的完整论文大纲。
user-invocable: true
disable-model-invocation: true
homepage: https://example.org/writeagent
metadata: {"openclaw":{"requires":{"bins":["python"]}}}
---

# 论文大纲与章节框架设计 Skill（接口骨架）

> 本文件作为接口契约，确保上下游可以按约定字段读取/写入 `state.json`。

## 何时使用

- `state.writing_task` 与 `state.literature_report` 均已就绪。
- `state.outline` 缺失或用户显式要求重新生成大纲。
- 用户提到"大纲 / 章节框架 / outline / 结构"。

## 调用方式

```bash
python {baseDir}/scripts/run.py --state {workspace}/state.json
```

## 输入

- `state.writing_task`（`schemas/writing_task.schema.json`）
- `state.literature_report`（`schemas/literature_report.schema.json`）

## 输出

- `state.outline`（**严格符合** `schemas/paper_outline.schema.json`）
- `outputs/03-论文详细大纲.md` —— 人类可读 Markdown

### 必须填充的字段

- `total_word_budget`：总字数（与 `writing_task.word_limit.total` 一致或合理偏离 ±20%）
- `sections[]`：完整章节树，每节包含：
  - `id`（如 `1.1`）、`title`、`level`、`parent_id`、`key_points[]`
  - `transition_note` —— 与前后章节的逻辑衔接说明
  - `word_budget` —— 字数预算
  - `supporting_papers[]` —— 引用 `literature_report.papers.id`

## 约束

- 章节层级 ≤ 3 级（除非论文超过 12000 字才考虑 4 级）。
- 每个有正文的章节必须至少绑定 1 篇支撑文献，除非是"结论 / 摘要"类。
- 字数预算总和必须等于 `total_word_budget`（允许 ±5% 误差）。

## 与下游 Skill 4 的契约

- Skill 4 按 `sections[]` 顺序生成正文；不会重新排序章节。
- Skill 4 会读取 `key_points` 作为撰写要点、`supporting_papers` 决定引用范围。

## 异常情况

- 文献覆盖不足：在 stderr 给出提示，但仍正常生成大纲。
- 字数分配不平衡（最大 / 最小章节 > 5x）：自动启动 normalization pass。

## TODO（组员 2 完成）

- [ ] `scripts/run.py` 主入口
- [ ] `scripts/prompts.py` 大纲生成提示词
- [ ] `scripts/balance.py` 字数预算 normalization
- [ ] `scripts/renderer.py` Markdown 渲染
- [ ] `references/` 各论文类型的大纲范例
