# Per-Paper Source Map Template

Source note: adapted from the MIT-licensed `office-academic-skill` report structure in `zLanqing/codex-claude-academic-skills`, reduced to the fields required by writeAgent's `literature_report`.

Create one entry per paper before running the script.

```json
{
  "paper_id": "BibTeX key",
  "research_question": "该文研究什么问题",
  "core_method": "核心方法、系统、框架或分析方式",
  "main_finding": "主要发现，必须来自摘要、正文或用户提供材料",
  "abstract_zh": "面向报告输出的中文摘要；英文原文只作为证据来源，不直接复制进报告",
  "main_finding_zh": "面向报告输出的中文主要发现",
  "key_claims": [
    "可用于论文相关工作的中文主张 1",
    "可用于论文相关工作的中文主张 2"
  ],
  "key_claims_zh": [
    "优先用于报告输出的中文核心观点 1",
    "优先用于报告输出的中文核心观点 2"
  ],
  "evidence_strength": "strong|moderate|weak",
  "source_urls": ["https://..."],
  "source_artifact_ids": ["extract-..."],
  "limitations": [
    {"label": "原文", "text": "..."},
    {"label": "推断", "text": "..."}
  ],
  "limitations_zh": [
    {"label": "原文", "text": "..."},
    {"label": "推断", "text": "..."}
  ],
  "alignment_to_core": [
    {"core_argument_index": 0, "stance": "supports", "note": "..."}
  ],
  "provenance": {
    "main_finding": "paper_reading_card|extract_sources|abstract",
    "limitations": "推断: 基于未覆盖的评测范围"
  }
}
```

Prefer deriving this entry from `paper_reading_cards[]`. If no card, source URL, or extraction artifact exists, keep `evidence_strength` as `weak`.

## Evidence Strength

- `strong`: peer-reviewed or directly supported by concrete evaluation.
- `moderate`: preprint, benchmark, or system paper with plausible but partial evidence.
- `weak`: documentation, project page, commentary, or metadata-only source.

## Stance Values

- `supports`: directly supports a core argument.
- `extends`: provides a broader method, framework, or adjacent evidence.
- `contradicts`: introduces a limitation or counterpoint.
- `background`: useful context without direct support.
