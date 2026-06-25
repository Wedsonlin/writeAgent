---
name: academic-formatting
description: 将 Skill4 的 draft 规范化为 formatted_draft，统一标题层级、摘要/关键词、图表题注、正文 [n] 引用、参考文献格式，并导出 Markdown + DOCX，PDF 可用时导出。Use when academic_formatting stage, draft exists, or user mentions 格式规范, DOCX, PDF, GB/T 7714, 引用标注, 图表编号. 不润色、不改论点。
metadata: {"openclaw":{"requires":{"bins":["python"]}}}
---

# Academic Formatting

## Scope

Skill5 是“格式规范化与导出中间稿”阶段。它只处理论文初稿的学术格式：标题层级、摘要与关键词呈现、图表编号和题注、正文 `[n]` 引用、参考文献排版、DOCX/PDF 导出状态。

不要在本 Skill 中润色语言、改写论点、补充文献、重写章节或改变证据关系。语言润色与查重建议属于 Skill6。

## Inputs

优先读取完整 `draft` JSON；如果同时提供 `draft_markdown` 或 `draft_markdown_path`，可用作人工语义核对，但脚本契约以 `draft` JSON 为准。读取已有 artifact 时必须读取完整文件：如果第一次读取被截断，应提高读取行数或重新读取，不能凭截断内容重建 draft，更不能遗漏 `draft.references[]`。

可选输入：

- `formatting_constraints`：目标期刊、学校或课程格式要求。
- `target_template` / 模板说明：字体、字号、行距、引用样式、标题层级、图表题注规则。
- `formatting_constraints.template_profile` / `template_source_path`：当指向 `case/references/软件学报排版样例2025年版.doc` 时，使用 `journal_of_software_2025`。

缺省格式约束：

- 引用样式：`GB/T 7714`
- 正文引用：数字方括号 `[n]`
- 摘要标题：`## 摘要`
- 正文默认中文学术排版
- DOCX 必须生成；PDF 尽力生成，失败时记录 unavailable reason
- case 中存在软件学报排版样例时，DOCX 采用 `journal_of_software_2025`：正文 `[n]`、`[n,m]`、`[n-m]` 作为右上标，参考文献编号保持普通文本。

## Process Knowledge

1. 读取 `draft.title`、`abstract`、`keywords`、`sections[]`、`references[]`，确认 draft 是完整论文初稿。
2. 按目标模板规范标题层级，消除标题跳级，摘要和关键词不作为普通正文节重复渲染。
3. 将正文引用统一为 `[n]`；所有 `[n]` 必须能映射到 `references[]`。
4. 参考文献在报告内部按 `[n] GB/T 7714 entry` 渲染，不生成单独参考文献 artifact。
5. 检查图表题注：出现图片或表格时，应有“图 1 …”或“表 1 …”这类编号题注。
6. 调用 `scripts/run.py` 作为确定性契约门，生成 JSON、Markdown sidecar、DOCX，并记录 PDF 状态。
7. 对模板化导出写入 `template_profile`、`template_source_path`、`template_conformance_report`；Markdown 仅是预览，真正的右上标引用以 DOCX/PDF 为准。

按需阅读：

- `references/formatting/heading-rules.md`
- `references/formatting/in-text-citation-rules.md`
- `references/formatting/gb7714-bibliography.md`
- `references/formatting/target-template.md`
- `references/formatting/document-export.md`
- `references/formatting/figure-table-captions.md`

## Script Contract

运行脚本：

```text
python skill_packs/academic-paper-writing/skills/academic-formatting/scripts/run.py --input path/to/input.json --output path/to/output.json
```

成功输出：

```json
{
  "artifact_type": "formatted_draft",
  "formatted_draft": {
    "normalized_draft": {},
    "markdown": "# 论文标题\n\n## 摘要\n\n...",
    "markdown_path": "path/to/output.md",
    "docx_path": "path/to/output.docx",
    "pdf_path": "path/to/output.pdf 或 null",
    "template_profile": "journal_of_software_2025",
    "template_source_path": "case/references/软件学报排版样例2025年版.doc",
    "template_conformance_report": {},
    "export_status": {
      "docx": {"status": "generated", "path": "path/to/output.docx"},
      "pdf": {"status": "generated 或 unavailable", "path": "path/to/output.pdf 或 null"}
    },
    "format_check_report": {},
    "issues": [],
    "quality_checks": {}
  }
}
```

失败输出：

```json
{
  "artifact_type": "formatted_draft",
  "error": {
    "message": "draft.sections is required",
    "fields": ["draft.sections"]
  }
}
```

核心 schema：

- `references/contracts/input.schema.json`
- `references/contracts/formatted-draft.schema.json`

示例输入：

- `assets/input.example.json`
- `assets/draft.sample.json`
- `assets/draft.raw.sample.json`

## Quality Checks

`quality_checks` 至少包含：

- `headings_normalized`
- `references_formatted`
- `figures_tables_labeled`
- `docx_exported`
- `pdf_exported`

正文存在 `[n]` 或 `citations_used[]` 时，`draft.references[]` 为空是阻塞错误。DOCX 失败也是阻塞错误；PDF 失败不是阻塞错误，但必须写入 `export_status.pdf.status = "unavailable"` 和原因。

## Completion Criteria

完成前确认：

- `artifact_type == "formatted_draft"`。
- Markdown sidecar 存在且内容与 JSON 中 `markdown` 一致。
- `docx_path` 存在、非空、可作为 DOCX 文件打开。
- `pdf_path` 生成或 `export_status.pdf` 明确 unavailable reason。
- 参考文献仍在报告内部；没有生成单独 bibliography artifact。
- 任何 `issues[]` 中的 fixed/warning 都如实保留，不宣称未通过的格式项已经通过。
