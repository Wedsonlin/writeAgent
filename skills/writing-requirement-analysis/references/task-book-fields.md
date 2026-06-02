# 论文写作任务书字段说明

完整的 JSON Schema 见 [`schemas/writing_task.schema.json`](../../../schemas/writing_task.schema.json)。
本文件用人类可读语言解释每个字段的语义与边界，供 LLM 抽取时参考。

## 顶层字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `topic` | string | 论文核心主题。**必填**，一句完整中文/英文。 |
| `paper_type` | enum | survey / empirical / theoretical / system / case_study / position。 |
| `language` | enum | 论文语言：zh / en / bilingual。默认 zh。 |
| `target_journal` | object | 详见下表。 |
| `word_limit` | object | `total` 字数下限 1000；`by_chapter` 可选。 |
| `core_arguments` | array<string> | **至少 1 条**，每条 ≤ 60 字。 |
| `innovation_points` | array<string> | 创新点/贡献。 |
| `research_scope` | object | `domain` / `subtopics` / `boundary`。 |
| `chapter_framework` | array | 顶层章节（一级 + 可选二级）。 |
| `references_seed` | array | 用户提供的初始文献清单。 |
| `missing_info` | array | Skill 自动识别的缺失字段。 |

## target_journal

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `name` | 是 | 期刊名称；用户未指定时填 "未指定"。 |
| `level` | 否 | CCF-A / CCF-B / CCF-C / SCI / EI / 中文核心 / 未指定 / 其他。 |
| `style_profile.citation_style` | 否 | GB/T 7714 / APA / IEEE / ACM / Chicago。 |
| `style_profile.tone` | 否 | formal-zh / formal-en / narrative。 |
| `style_profile.structure_hint` | 否 | 一句话顶层结构提示。 |

## missing_info 项

`criticality`：

- `blocker` —— 不补齐就无法继续生成任务书；Agent 应向用户澄清。
- `important` —— 缺失会显著降低质量，但可暂时占位；用户在后续轮次再补充。
- `nice-to-have` —— 不影响主流程，仅作为提示。

## chapter_framework 单元

| 字段 | 说明 |
| --- | --- |
| `chapter_id` | 形如 `1` / `1.1` / `2.3` 的章节编号。 |
| `title` | 章节标题。 |
| `key_points` | 本章核心要点。 |
| `word_budget` | 字数预算（int）。 |
| `depends_on` | 可选：前置章节 id 列表，用于 Skill 4 决定撰写顺序。 |
