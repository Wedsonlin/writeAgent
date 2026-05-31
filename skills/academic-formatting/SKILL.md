---
name: academic-formatting
description: 学术格式排版与规范校验 Skill。当 state.draft 已生成、state.formatted_draft 仍为空时触发；或用户提到"格式校验/排版/Word 导出/PDF 导出/参考文献排序"时触发。统一标题层级、字体行距、图表编号、引用格式与参考文献排序，并产出校验报告。
user-invocable: true
disable-model-invocation: false
homepage: https://example.org/writeagent
metadata: {"openclaw":{"requires":{"bins":["python"],"env":["WRITEAGENT_LLM_API_KEY"]},"primaryEnv":"WRITEAGENT_LLM_API_KEY"}}
---

# 学术格式排版与规范校验 Skill（接口骨架）

> 本文件作为接口契约。

## 何时使用

- `state.draft` 就绪、`state.formatted_draft` 缺失。
- 用户提到"格式 / 排版 / Word 导出 / PDF / 参考文献排序 / 引用格式"。

## 调用方式

```bash
python {baseDir}/scripts/run.py --state {workspace}/state.json \
    [--target-format docx|pdf|markdown] \
    [--template path/to/template.docx]
```

## 输入

- `state.draft`（`schemas/paper_draft.schema.json`）
- `state.writing_task.target_journal.style_profile`（决定引用格式、字体、行距）
- `state.literature_report.formatted_bibliography`（已规范化的引用列表）

## 输出

- `state.formatted_draft`（**严格符合** `schemas/format_report.schema.json`）
- `outputs/05-格式规范论文终稿.{md,docx,pdf}`
- `outputs/05-格式校验报告.md`

### 必须填充的字段

- `normalized_draft`：格式标准化后的论文（结构同 draft）
- `export_paths`：导出文件的相对/绝对路径（至少包含 markdown）
- `issues[]`：每条校验问题包含 `category`、`location`、`severity`、`message`、`suggestion`

## 与下游 Skill 6 的契约

- Skill 6 接受 `formatted_draft.normalized_draft` 作为输入。
- 导出文件的路径写入 `export_paths`，方便用户下载。

## 校验维度

| category | 检查内容 |
| --- | --- |
| `heading` | 标题层级是否一致；编号是否连续 |
| `font` | 字体字号是否匹配 style_profile |
| `spacing` | 行距、段间距 |
| `figure` | 图编号、引用、说明完整性 |
| `table` | 表编号、引用、表头 |
| `citation` | 引用格式是否匹配 citation_style |
| `bibliography` | 参考文献排序、重复、漏引 |

## 异常情况

- 缺少 docx 模板：仅产出 markdown 版本；issues 中加 `warning`。
- 引用编号断号：自动 renumber，并在 issues 中说明。

## TODO（组员 3 完成）

- [ ] `scripts/run.py`
- [ ] `scripts/heading_normalize.py`
- [ ] `scripts/citation_check.py`
- [ ] `scripts/docx_export.py`（基于 python-docx）
- [ ] `scripts/pdf_export.py`（可选，基于 pandoc / weasyprint）
- [ ] `references/` 主流期刊模板规范
- [ ] `assets/` Word 模板文件
