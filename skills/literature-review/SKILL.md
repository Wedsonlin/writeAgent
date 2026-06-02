---
name: literature-review
description: 文献梳理与引用整合 Skill。当用户提到"文献综述/参考文献整理/引用规范/literature review/research gap"或 writing_task 已存在但 literature_report 尚未生成时使用。本 Skill 不直接调用模型；应先由文献分析/综合 Sub-agent 写入 state.intermediate.literature_review，再运行 scripts/run.py 解析文献、格式化引用、组装报告并写入 state.literature_report。
user-invocable: true
disable-model-invocation: true
homepage: https://example.org/writeagent
metadata: {"openclaw":{"requires":{"bins":["python"]}}}
---

# 文献梳理与引用整合

把用户提供的参考文献（BibTeX / PDF / 纯文本）转化为一份结构化的**文献梳理报告**（`literature_report`），为 Skill 3 大纲与 Skill 4 正文生成提供文献支撑。

本 Skill 遵循 Agent-native 分工：

- Main Agent 判断是否需要文献梳理。
- Literature analysis Sub-agent 生成 `paper_claims`。
- Literature synthesis Sub-agent 生成 `synthesis`。
- `scripts/run.py` 执行文献采集、去重、引用格式化、报告组装、schema validation 和落盘。
- Skill script 不直接调用 LLM。

## 何时使用

满足以下任一条件即触发：

- `state.writing_task` 已生成；`state.literature_report` 仍为空。
- 用户提到"梳理文献 / 研究现状 / 文献综述 / literature review / 研究缺口 / 参考文献规范"。
- 用户提供了新的 `.bib` 文件或 PDF 目录希望加入综述。

## Agent 使用流程

### 1. 派生文献观点提取 Sub-agent

生成：

```jsonc
{
  "intermediate": {
    "literature_review": {
      "paper_claims": [
        {
          "id": "paper-id",
          "key_claims": ["..."],
          "evidence_strength": "moderate",
          "methods": ["..."],
          "limitations": ["..."]
        }
      ]
    }
  }
}
```

推荐 `SubAgentSpec`：

```json
{
  "role": "literature analysis specialist",
  "task": "Extract key claims, methods, evidence strength, and limitations from collected reference papers.",
  "input_keys": ["writing_task", "references.raw_papers"],
  "output_key": "intermediate.literature_review.paper_claims",
  "skill_context": ["literature-review"],
  "prompt_refs": ["skills/literature-review/prompts/extract_claims.md"],
  "output_schema": "PaperClaimsExtraction",
  "allowed_tools": ["inspect_state_subset", "read_skill_prompt", "read_skill_context"]
}
```

### 2. 派生文献综合 Sub-agent

生成：

```jsonc
{
  "intermediate": {
    "literature_review": {
      "synthesis": {
        "clusters": [],
        "timeline_summary": "...",
        "consensus": [],
        "controversies": [],
        "research_gaps": [],
        "alignments": []
      }
    }
  }
}
```

### 3. 运行确定性入口

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

调用前置：

- `state.writing_task` 必须存在。
- `state.intermediate.literature_review.paper_claims` 必须存在。
- `state.intermediate.literature_review.synthesis` 必须存在。

## 处理流程

1. **采集**：用 `parsers/bibtex.py`、`parsers/pdf.py` 解析三类输入，得到统一的 `RawPaper` 列表（含 title、authors、year、venue、abstract、source_kind 等）。
2. **合并 claims**：读取 `state.intermediate.literature_review.paper_claims`，把 `key_claims` 与 `evidence_strength` 合并进文献记录。
3. **合并 synthesis**：读取 `state.intermediate.literature_review.synthesis`，生成研究脉络、共识、争议、研究缺口与 `alignment_to_core`。
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
- **缺少 paper_claims intermediate**：stderr 输出明确错误，exit code 1。Main Agent 应先派生 literature analysis Sub-agent。
- **缺少 synthesis intermediate**：stderr 输出明确错误，exit code 1。Main Agent 应先派生 literature synthesis Sub-agent。
- **无任何输入文献**：Skill 仍然产出 report，但 `papers=[]` 且 `research_landscape.clusters=[]`，并在 stderr 提示。

## 过程知识

- `prompts/extract_claims.md`：供 Sub-agent 提取文献观点。
- `prompts/synthesize.md`：供 Sub-agent 做研究脉络综合。
- `references/`：文献处理说明与示例素材。
- `scripts/parsers/*.py`：确定性文献解析 helper。
- `scripts/citation_formatter.py`：确定性引用格式化 helper。
- `scripts/*.py` 为内部 helper，不应由 Main Agent 自由组合调用。
