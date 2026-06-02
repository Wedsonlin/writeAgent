---
name: polish-and-plagiarism
description: 语言润色与查重优化 Skill。当 state.formatted_draft 已生成、state.polished_draft 仍为空时触发；或用户提到"润色/查重/降重/语言优化"时触发。优化语句流畅度与学术性，修正语法/标点/逻辑问题，针对查重报告中重复段落提供改写建议。
user-invocable: true
disable-model-invocation: true
homepage: https://example.org/writeagent
metadata: {"openclaw":{"requires":{"bins":["python"]}}}
---

# 语言润色与查重优化 Skill（接口骨架）

> 本文件作为接口契约。

## 何时使用

- `state.formatted_draft` 就绪、`state.polished_draft` 缺失。
- 用户提到"润色 / 查重 / 降重 / 语法 / 流畅度"。

## 调用方式

```bash
python {baseDir}/scripts/run.py --state {workspace}/state.json \
    [--plagiarism-report path/to/report.{json,csv}] \
    [--target-rate 0.15]
```

## 输入

- `state.formatted_draft.normalized_draft`（`schemas/format_report.schema.json` 的子字段）
- `state.writing_task.target_journal.style_profile.tone`（润色风格）
- 可选：查重报告（`--plagiarism-report`）

## 输出

- `state.polished_draft`（**严格符合** `schemas/polish_report.schema.json`）
- `outputs/06-润色优化后论文终稿.md`
- `outputs/06-润色说明报告.md`
- `outputs/06-查重优化建议.md`（可选）

### 必须填充的字段

- `polished_draft`：润色后的论文（结构同 draft）
- `polish_log[]`：每条变更含 `location`、`change_type`、`before`、`after`、`reason`
- `plagiarism_optimization[]`（可选）：针对查重报告的降重建议

## 与上游契约

- **必须保留**原稿的核心论点与研究结论，不得改变事实/数据。
- 引用与文献顺序不得改变（Skill 5 已处理）。
- 章节顺序与 id 与 `formatted_draft` 完全一致。

## 润色维度

| change_type | 内容 |
| --- | --- |
| `grammar` | 语法错误 |
| `punctuation` | 标点 |
| `concise` | 冗余精简 |
| `rephrase` | 句式重写 |
| `logic` | 逻辑顺序优化 |
| `tone` | 语气统一为学术风格 |

## 降重策略（可选）

- 同义改写、句式重组（不损失信息量）。
- 拆分长句、合并冗余短句。
- 把直接引用转为间接引用（保留 citation）。

## 异常情况

- 润色后字数偏离 ±20%：触发回退，提示用户审阅。
- 查重报告解析失败：跳过降重段，仅输出语言润色结果。

## TODO（组员 3 完成）

- [ ] `scripts/run.py`
- [ ] `scripts/polish.py`
- [ ] `scripts/plagiarism_report_parser.py`
- [ ] `scripts/diff_renderer.py`（产出 polish_log 的可读 diff）
- [ ] `references/` 学术润色规则与典型修改示例
