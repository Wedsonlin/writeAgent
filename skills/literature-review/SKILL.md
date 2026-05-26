---
name: literature-review
description: 文献梳理与引用整合 Skill。当用户提到"文献综述/参考文献整理/引用规范/literature review/research gap"或写作任务书已存在但 literature_report 尚未生成时调用。读取 BibTeX/PDF/纯文本三类参考文献，输出含研究脉络、共识、争议、研究缺口、规范引用列表（GB/T 7714 + APA）的文献梳理报告。
user-invocable: true
disable-model-invocation: false
homepage: https://example.org/writeagent
metadata: {"openclaw":{"requires":{"bins":["python"],"env":["WRITEAGENT_LLM_API_KEY"]},"primaryEnv":"WRITEAGENT_LLM_API_KEY"}}
---

# 文献梳理与引用整合

把用户提供的参考文献（BibTeX / PDF / 纯文本）转化为一份结构化的**文献梳理报告**（`literature_report`），为 Skill 3 大纲与 Skill 4 正文生成提供文献支撑。

## 何时使用

满足以下任一条件即触发：

- `state.writing_task` 已生成；`state.literature_report` 仍为空。
- 用户提到"梳理文献 / 研究现状 / 文献综述 / literature review / 研究缺口 / 参考文献规范"。
- 用户提供了新的 `.bib` 文件或 PDF 目录希望加入综述。

## 调用方式

```bash
python {baseDir}/scripts/run.py --state {workspace}/state.json \
    [--refs path/to/*.bib] [--pdf-dir path/to/pdfs/] [--text-file notes.md] \
    [--citation-style "GB/T 7714"]
```

参数：

- `--state` **必填**。共享 `state.json` 路径。
- `--refs` 可重复。`.bib` 文件路径。
- `--pdf-dir` 可选。包含 PDF 文献的目录（递归读取所有 .pdf）。
- `--text-file` 可重复。纯文本笔记文件（每段一条文献，或自由记述）。
- `--citation-style` 可选。`GB/T 7714` | `APA` | `IEEE` | `ACM` | `Chicago`，默认取 `writing_task.target_journal.style_profile.citation_style` 或 `GB/T 7714`。

若三个输入参数都未给定，Skill 会回退到 `state.writing_task.references_seed` 列出的路径。

## 处理流程

1. **采集**：用 `parsers/bibtex.py`、`parsers/pdf.py` 解析三类输入，得到统一的 `RawPaper` 列表（含 title、authors、year、venue、abstract、source_kind 等）。
2. **抽取**：对每篇 paper，调用 LLM `prompts.EXTRACT_PROMPT` 抽取 `key_claims` 与 `evidence_strength`。
3. **聚类与对齐**：调用 LLM `prompts.SYNTHESIS_PROMPT` 完成（a）按主题聚类、（b）总结研究脉络、（c）识别共识/争议/研究缺口、（d）把每篇 paper 与 `writing_task.core_arguments` 对齐。
4. **引用格式化**：`citation_formatter.py` 同时生成 GB/T 7714-2015 与 APA 7 两套规范引用。
5. **校验**：用 `_shared.schemas.LiteratureReport` 做 pydantic 验证。
6. **持久化**：`literature_report` 写入 `state.json`，Markdown 报告写入 `outputs/02-文献梳理报告.md`。

## 输出

- `state.literature_report`（符合 `schemas/literature_report.schema.json`）。
- `outputs/02-文献梳理报告.md` —— 人类可读 Markdown。
- stdout —— 简短摘要（含文献条数、聚类数、缺口数）。

## 异常情况

- **BibTeX 解析失败**：跳过该条目并记入 `history.message`，不让单篇错乱破坏全局。
- **PDF 无文本（纯扫描件）**：跳过 abstract，仅保留 filename → title 的启发式标题，并标记 `evidence_strength=anecdotal`。
- **LLM 抽取失败**：自动重试 1 次；仍失败则把该文献 `key_claims=[]`，确保流水线不中断。
- **无任何输入文献**：Skill 仍然产出 report，但 `papers=[]` 且 `research_landscape.clusters=[]`，并在 stderr 提示。

## Mock 模式

`WRITEAGENT_MOCK_LLM=1` 时使用 `scripts/mock.py` 的桩响应，可在无网络下端到端跑通。
