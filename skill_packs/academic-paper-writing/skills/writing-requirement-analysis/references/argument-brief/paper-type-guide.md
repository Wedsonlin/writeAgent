# Paper Type Guide

Use this file when `argument_brief.venue.paper_type` or the section plan is unclear.

Skill1 supports only two paper types. If the user's wording does not clearly map to one of them, call `ask_user` and ask them to choose “综述” or “研究型论文”.

## `survey`

Use for papers whose contribution is taxonomy, comparison, trend analysis, and research-gap synthesis.

Accepted user wording:

- 综述
- 综述类论文
- 综述论文
- survey

Expected sections:

- 引言
- 文献范围与检索策略
- 主题分类框架
- 代表性工作分析
- 挑战与趋势
- 结论

## `research`

Use for research papers whose contribution is a method, system, experiment, theoretical analysis, dataset, case study, or evaluative argument. Skill1 does not split these into subtypes; later stages refine the internal structure.

Accepted user wording:

- 研究型论文
- 研究论文
- research

Expected sections:

- 引言
- 相关工作
- 方法或系统设计
- 实验设计
- 结果与讨论
- 结论

## Decision Rule

When the paper mixes survey content with an original method, system, experiment, or case analysis, choose `research` if the user's own contribution is the main object of evaluation. Choose `survey` only when literature synthesis itself is the main contribution.
