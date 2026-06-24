# Paper Reading Card

Use this reference when turning a seed BibTeX entry or supplementary search result into `paper_reading_cards[]`.

## Required Shape

```json
{
  "paper_id": "BibTeX key",
  "source_urls": ["https://paper-or-project-page"],
  "source_artifact_ids": ["search-or-extract-artifact-id"],
  "reading_status": "read|partial|unavailable",
  "research_problem_zh": "论文研究的问题",
  "method_zh": "核心方法、系统设计或分析方式",
  "main_claims_zh": ["具体、非模板化的核心观点"],
  "evidence_zh": ["来自摘要、正文、项目文档或元数据抽取结果的证据摘要"],
  "limitations_zh": ["论文自身限制或谨慎推断的边界"],
  "relevance_to_arguments": [
    {
      "core_argument_index": 0,
      "stance": "supports|extends|contradicts|background",
      "support_strength": "strong|moderate|weak",
      "evidence_summary_zh": "该文献如何支撑、扩展或限制任务书核心论点"
    }
  ],
  "relevance_to_innovations": [
    {
      "innovation_index": 0,
      "stance": "supports|extends|contradicts|background",
      "support_strength": "strong|moderate|weak",
      "evidence_summary_zh": "该文献如何支撑、扩展或限制任务书创新点"
    }
  ]
}
```

## Quality Rules

- `main_claims_zh` must mention the actual system, method, mechanism, metric, or finding. Avoid repeated frames such as “该文献围绕……讨论……” across many papers.
- `strong` support requires extracted source content or reliable full-text/project documentation plus a direct match to a core argument or innovation point.
- `moderate` support requires extracted source content or reliable metadata plus a plausible but partial match.
- `weak` support is required when only title, BibTeX metadata, search snippet, or unavailable extraction exists.
- `source_urls` and `source_artifact_ids` are mandatory for `strong` or `moderate` support.
- Preserve English titles, system names, model names, acronyms, DOI, URL, and citation keys; write the analytical content in Chinese.
