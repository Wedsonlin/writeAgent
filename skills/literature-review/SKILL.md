---
name: literature-review
description: 梳理参考文献并生成结构化文献综述报告。Use when the user mentions 文献综述, 研究现状, research gap, literature review, references, citation formatting, or needs evidence support for a writing task.
user-invocable: true
disable-model-invocation: true
homepage: https://example.org/writeagent
metadata: {"openclaw":{"requires":{"bins":["python"]}}}
---

# 文献梳理与引用整合

把 BibTeX、PDF 或纯文本参考资料转化为结构化**文献梳理报告**（`literature_report`），为大纲和正文写作提供研究脉络、共识、争议、缺口与规范参考文献。

## 何时使用

满足以下任一条件即触发：

- 用户提到"梳理文献 / 研究现状 / 文献综述 / literature review / 研究缺口 / 参考文献规范"。
- 用户提供了新的 `.bib` 文件或 PDF 目录希望加入综述。
- 写作任务已有主题和核心论点，但缺少文献证据支撑。
- 需要把零散参考文献整理为可复用的综述材料。

## 输入

- `writing_task`：主题、研究范围、核心论点和参考文献线索。
- BibTeX 文件、PDF 目录或纯文本文献笔记。
- 可选人工摘要：每篇文献的核心观点、方法、证据强度、局限。

## 工作流

Use this checklist:

```text
Literature review:
- [ ] Collect references from BibTeX, PDF, text notes, or `writing_task.references_seed`.
- [ ] Normalize paper metadata: title, authors, year, venue, abstract, DOI/URL, source kind.
- [ ] Extract each paper's key claims, methods, evidence strength, and limitations.
- [ ] Group papers into research clusters and summarize the field timeline.
- [ ] Identify consensus, controversies, and research gaps relevant to the writing task.
- [ ] Align useful papers to `writing_task.core_arguments`.
- [ ] Render the literature report and bibliography for human review.
```

## 结构化内容要求

### Paper Claims

每篇文献应包含：

- `id` 或 `paper_id`：必须能与文献记录对应。
- `key_claims`：文献的主要结论，不要写成泛泛摘要。
- `evidence_strength`：`strong` / `moderate` / `weak` / `anecdotal`。
- `methods`：研究方法、数据来源或系统实现方式。
- `limitations`：作者承认的限制或可推断的证据边界。

### Synthesis

综合结果应包含：

- `clusters`：研究主题簇，每个簇包含名称、摘要和代表文献。
- `timeline_summary`：领域演进主线，避免逐篇罗列。
- `consensus`：多数文献支持的共同观点。
- `controversies`：相互冲突的观点、方法或证据。
- `research_gaps`：可服务于当前论文创新点的缺口。
- `alignments`：文献与 `writing_task.core_arguments` 的对应关系。

## 确定性辅助脚本

本仓库提供脚本用于采集文献、去重、格式化引用、组装报告和渲染 Markdown：

```bash
python {baseDir}/scripts/run.py --state {workspace}/state.json \
    [--refs path/to/*.bib] [--pdf-dir path/to/pdfs/] [--text-file notes.md] \
    [--citation-style "GB/T 7714"]
```

参数：

- `--state` 必填。共享运行上下文路径。
- `--refs` 可重复。`.bib` 文件路径。
- `--pdf-dir` 可选。包含 PDF 文献的目录（递归读取所有 .pdf）。
- `--text-file` 可重复。纯文本笔记文件（每段一条文献，或自由记述）。
- `--citation-style` 可选。记录首选引用风格；当前报告固定渲染 GB/T 7714-2015 与 APA 7 两套参考文献。

若三个文献输入参数都未给定，脚本会回退到 `writing_task.references_seed` 列出的路径。

不要直接组合调用 `scripts/parsers/*.py` 或 `scripts/citation_formatter.py`；优先使用 `scripts/run.py`。

## 输出

- `literature_report` JSON（符合 `schemas/literature_report.schema.json`）。
- `outputs/02-文献梳理报告.md`：人类可读 Markdown 文献报告。
- 规范参考文献：当前固定包含 GB/T 7714-2015 与 APA 7。

## 异常与降级

- BibTeX 单条解析失败：跳过该条并记录 warning，不让单篇错误破坏全局。
- PDF 无文本或纯扫描件：保留可推断标题，证据强度按低可信处理。
- 无任何输入文献：仍可生成空报告，但必须提示用户补充文献。
- schema validation warning：先修正字段结构，再继续下游写作。

## 验证

完成后检查：

- 文献条目数量符合用户输入或 `references_seed`。
- 每篇关键文献至少有 1 条 `key_claims`，且证据强度不是无依据填充。
- `research_gaps` 能对应当前论文主题或核心论点。
- `controversies` 写清冲突双方，而不是只列关键词。
- Markdown 报告包含研究脉络、共识、争议、缺口、文献明细和参考文献。

## 参考资料

- [prompts/extract_claims.md](prompts/extract_claims.md)：文献观点抽取提示。
- [prompts/synthesize.md](prompts/synthesize.md)：研究脉络综合提示。
- [references/review-template.md](references/review-template.md)：报告结构模板。
- [references/gb7714-rules.md](references/gb7714-rules.md)：GB/T 7714-2015 规则。
- [references/apa-rules.md](references/apa-rules.md)：APA 7 规则。
- [assets/example_output.md](assets/example_output.md)：文献报告输出示例。
