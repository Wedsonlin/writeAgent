---
name: writing-requirement-analysis
description: 分析论文写作需求并生成结构化写作任务书。Use when the user mentions 写论文, 任务书, 选题, 投稿, 研究方向, 写作要求, or needs a thesis/article brief before drafting.
user-invocable: true
disable-model-invocation: true
homepage: https://example.org/writeagent
metadata: {"openclaw":{"requires":{"bins":["python"]}}}
---

# 写作需求分析与选题定位

把"想写一篇论文"这类模糊请求转化为机器可消费、人类可读的**论文写作任务书**（`writing_task`），为文献梳理、大纲和正文写作提供稳定输入。

## 何时使用

满足任一条件即可触发：

- 用户提到"写论文"、"论文写作"、"投稿"、"任务书"、"选题"、"研究方向"。
- 需要把口语化写作要求整理成可执行的论文任务书。
- 已有任务书但用户明确要求"重新定位选题"、"调整研究范围"或"改投稿目标"。

## 输入

- 用户原始写作请求。
- 可选约束：论文类型、目标期刊/会议、语言、字数、研究范围、核心论点、参考文献线索。
- 可选已有草稿：不完整的 `writing_task` 或人工填写的任务书片段。

## 工作流

Use this checklist:

```text
Requirement analysis:
- [ ] Extract the topic, paper type, language, journal target, word budget, scope, and core arguments.
- [ ] Select a `paper_type`; default to `survey` only when the request is underspecified.
- [ ] Preserve user-provided constraints instead of replacing them with defaults.
- [ ] Add unresolved critical questions to `missing_info` rather than blocking the task.
- [ ] Build or complete `chapter_framework` from the paper type and word budget.
- [ ] Render a readable task book for human review.
```

## 输出

- `writing_task` JSON（符合 `schemas/writing_task.schema.json`）。
- `outputs/01-论文写作任务书.md`：人类可读 Markdown 任务书。
- `missing_info[]`：仍需用户补充的问题，按 `blocker` / `important` / `nice-to-have` 标注优先级。

## 字段质量规则

- `topic` 应是一句清晰的论文主题，不要只写关键词。
- `paper_type` 只能使用 `survey` / `empirical` / `theoretical` / `system` / `case_study` / `position`。
- `core_arguments` 至少 1 条；缺失时在 `missing_info` 标记为 `blocker`。
- `innovation_points` 可以暂缺，但应在 `missing_info` 标记为 `important`。
- `target_journal.name` 未指定时填 `"未指定"`，不要编造期刊。
- `references_seed` 只记录用户明确提供或可定位的文献线索。
- `chapter_framework` 应包含章节标题、关键要点和字数预算。

## 确定性辅助脚本

本仓库提供脚本用于校验、补全期刊风格、生成章节模板并渲染 Markdown：

```bash
python {baseDir}/scripts/run.py --state {workspace}/state.json [--user-request "..."]
```

脚本会：

- 匹配 `references/journal-styles.md` 中的期刊风格画像。
- 按 `paper_type` 和总字数补齐章节框架。
- 检测关键缺失信息并写入 `missing_info[]`。
- 生成 `outputs/01-论文写作任务书.md`。

不要直接组合调用 `scripts/*.py` 内部 helper；优先使用 `scripts/run.py`。

## 验证

完成后检查：

- `writing_task.topic`、`paper_type`、`core_arguments` 非空且与用户请求一致。
- `missing_info` 中的 `blocker` 项确实无法从现有请求推断。
- 章节字数预算合计接近 `word_limit.total`。
- Markdown 任务书可供用户直接确认或修改。
- 若脚本输出 schema validation warning，先修正字段结构，再继续下游写作。

## 参考资料

- [prompts/extract_writing_task.md](prompts/extract_writing_task.md)：需求抽取提示。
- [references/task-book-fields.md](references/task-book-fields.md)：字段语义与边界。
- [references/paper-type-templates.md](references/paper-type-templates.md)：论文类型与章节模板。
- [references/journal-styles.md](references/journal-styles.md)：期刊风格画像。
- [assets/example_output.md](assets/example_output.md)：任务书输出示例。
