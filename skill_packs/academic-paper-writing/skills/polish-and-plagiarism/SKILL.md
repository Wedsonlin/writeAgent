---
name: polish-and-plagiarism
description: 基于 Skill5 formatted_draft 进行最终中文学术润色、重复表达优化建议与终稿导出，产出 polished_draft Markdown + DOCX，PDF 可用时导出。Use when polish_and_plagiarism stage, formatted_draft exists, or user mentions 润色, 查重, 降重, 终稿, polished_draft. 不改变核心论点、引用编号、参考文献或事实结论。
metadata: {"openclaw":{"requires":{"bins":["python"]}}}
---

# Polish and Plagiarism

## Scope

Skill6 是六阶段论文写作流程的最终产出阶段。它基于 `formatted_draft` 进行语言润色、重复表达优化建议和终稿导出，正式输出 `polished_draft`。

Skill6 不负责修复标题层级、重新排参考文献、补写正文、补充实验或新增文献。若发现格式问题，应记录 warning；不要把 Skill6 变成 Skill5 或 Skill4 的重跑。

本项目不接入商业查重 API。`plagiarism_optimization[]` 是基于输入文本和可选查重报告形成的改写建议，不等同于真实查重结果。

## Inputs

优先读取：

- `formatted_draft.markdown` 或 `formatted_draft.markdown_path`
- `formatted_draft` JSON 中的 `docx_path`、`format_check_report`、`issues[]`
- `formatted_draft.template_profile`、`template_source_path`、`template_conformance_report`：若存在，最终导出必须继承同一模板。

可选读取：

- `plagiarism_report`：外部查重报告，如用户提供。
- `protected_claims[]`：必须保留的核心论点、创新点或关键表述。
- `polish_constraints`：语气、语言、引用保护、标题保护。

## LLM Polishing Preflight

LLM-polished `polished_markdown` is required before the deterministic script runs. This Skill's language polishing, grammar correction, redundancy reduction, logic-smoothing, and similarity-reduction advice are performed by the LLM agent before `scripts/run.py`; the script only validates, checks preservation constraints, renders sidecars, and exports DOCX/PDF.

- Do not run `scripts/run.py` without `polished_markdown`.
- Do not preserve `formatted_draft.markdown` as the final manuscript unless it is explicitly copied into `polished_markdown` after the agent has reviewed it and recorded why no wording changes were needed.
- Do not rely on the script to create `polish_log`; the agent must provide a non-empty `polish_log[]` that explains changed sections, change types, and reasons.
- Provide `plagiarism_optimization[]` before the script runs. When no commercial plagiarism report is supplied, base the suggestions on repeated expressions, template-like sentences, and dense definition/list passages in the formatted draft.
- Before `scripts/run.py`, perform a heading and citation preservation gate: `polished_markdown` must keep the exact same Markdown heading lines as `formatted_draft.markdown`, and the multiset/count of every body citation marker `[n]` must match the formatted draft. The agent may improve paragraph wording, but must not add section numbering, remove headings, renumber citations, add extra markers, or drop existing markers.
- If the gate finds a mismatch, revise `polished_markdown` before running the script: restore the original heading line, restore the missing `[n]` marker near the same supported claim, or remove an extra marker introduced during polishing.
- If the deterministic script returns `heading_structure_changed`, `citation_marker_changed`, or `bibliography_changed`, treat it as a recoverable preservation error. Fix heading/citation/reference alignment and rerun the script instead of completing with unresolved final-manuscript warnings.

## Process Knowledge

1. 读取完整格式化稿，确认标题结构、引用编号和参考文献块存在。
2. 润色中文学术表达：提升严谨性、连贯性、术语一致性，删除口语化和空泛表达。
3. 降低重复：识别模板化句式、跨段重复、常见套话，给出 `plagiarism_optimization[]` 改写建议。
4. 严格保护：
   - 不改变 `protected_claims[]`。
   - 不删除、重排或改号正文 `[n]` 引用。
   - 不改变 `## 参考文献` 条目。
   - 不改变原有事实、数据、结论和文献归属。
5. 记录 `polish_log[]`，说明每类润色的位置、改动类型和原因。
6. 删除或改写写作流程泄漏文本，例如“本阶段生成”“阶段产物”“Skill4/Skill5 产物”“scripts/run.py”“ProgressLedger”。自然学术语境中的“发展阶段”可以保留。
7. 调用 `scripts/run.py` 作为确定性契约门，生成最终 JSON、Markdown sidecar、DOCX，并记录 PDF 状态；Skill6 的 DOCX 必须继承 Skill5 的模板 profile，不得回退为通用样式。

按需阅读：

- `references/polish/academic-tone-zh.md`
- `references/polish/citation-preservation.md`
- `references/polish/similarity-reduction.md`
- `references/polish/protected-claims.md`
- `references/polish/document-export.md`
- `references/polish/plagiarism-boundary.md`

## Script Contract

运行脚本：

```text
python skill_packs/academic-paper-writing/skills/polish-and-plagiarism/scripts/run.py --input path/to/input.json --output path/to/output.json
```

成功输出：

```json
{
  "artifact_type": "polished_draft",
  "polished_draft": {
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
    "polish_log": [],
    "plagiarism_optimization": [],
    "polish_report": {},
    "issues": [],
    "quality_checks": {},
    "source_formatted_path": "path/to/formatted.md"
  }
}
```

失败输出：

```json
{
  "artifact_type": "polished_draft",
  "error": {
    "message": "polish_log must be a non-empty array of edit records",
    "fields": ["polish_log"]
  }
}
```

核心 schema：

- `references/contracts/input.schema.json`
- `references/contracts/polished-draft.schema.json`

示例输入：

- `assets/input.example.json`
- `assets/polished.sample.json`
- `assets/polished.raw.sample.json`
- `assets/formatted_draft.sample.json`

## Quality Checks

`quality_checks` 至少包含：

- `polish_log_present`
- `tone_academic`
- `docx_exported`
- `pdf_exported`

`docx_exported` 必须为 true。PDF 失败不阻塞，但要记录 unavailable reason。

## Completion Criteria

完成前确认：

- `artifact_type == "polished_draft"`。
- `polished_draft.markdown_path` 存在且与 JSON 中 `markdown` 一致。
- `polished_draft.docx_path` 是 Skill6 重新导出的最终 DOCX，不是 Skill5 的中间 DOCX。
- 若 Skill5 使用 `journal_of_software_2025`，最终 DOCX 中正文引用必须为右上标，参考文献编号不能上标。
- `pdf_path` 生成或 `export_status.pdf` 明确 unavailable reason。
- `polish_log[]` 非空，并能解释主要润色动作。
- `plagiarism_optimization[]` 是建议，不声称已完成商业查重。
- 标题、正文 `[n]` 引用、参考文献块、protected claims 未被破坏。
- 如 `issues[]` 仍有 warning，必须如实报告，不宣称终稿完全无问题。
