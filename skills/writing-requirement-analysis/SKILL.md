---
name: writing-requirement-analysis
description: 论文写作需求分析与选题定位 Skill。当用户提出论文写作请求、提到"写论文/任务书/选题/期刊投稿/写作要求"时调用。输入用户自然语言需求，输出结构化论文写作任务书（含主题、论文类型、目标期刊、字数预算、核心论点、章节框架、缺失信息列表）。
user-invocable: true
disable-model-invocation: false
homepage: https://example.org/writeagent
metadata: {"openclaw":{"requires":{"bins":["python"],"env":["WRITEAGENT_LLM_API_KEY"]},"primaryEnv":"WRITEAGENT_LLM_API_KEY"}}
---

# 写作需求分析与选题定位

把用户对"写一篇论文"的模糊请求，转化为一份机器可消费、人类可读的**论文写作任务书**（writing_task），作为后续 5 个 Skill 的统一输入。

## 何时使用

满足任一条件即可触发：

- 用户提到"写论文"、"论文写作"、"投稿"、"任务书"、"选题"、"研究方向"。
- 在 writeAgent 流水线的开始阶段、`state.json` 中尚未填充 `writing_task`。
- 已有 `writing_task` 但用户明确要求"重新定位选题/调整任务书"。

## 调用方式

```bash
python {baseDir}/scripts/run.py --state {workspace}/state.json [--user-request "..."]
```

参数：

- `--state` 必填。指向共享 `state.json`（OpenClaw 默认 `~/.openclaw/workspace/.writeagent/state.json`）。
- `--user-request` 可选。若提供则覆盖 `state.user_request`；否则从 state 中读取。

调用前置：`state.json` 必须存在（即便仅含 `{"case_id":..., "user_request": "..."}` 也可）。Skill 会在缺失时创建一个最小骨架。

## 处理流程

1. 读取 `state.user_request` 与可选半结构化提示（如 `state.context_hints`）。
2. 调用 LLM 用 `prompts.STRUCTURED_EXTRACTION_PROMPT` 抽取字段（JSON 模式）。
3. 根据 `target_journal.name` 与 `target_journal.level` 在 `references/journal-styles.md` 中匹配风格画像（`style_profile`）。
4. 根据 `paper_type` 加载 `references/paper-type-templates.md` 中的章节模板，生成 `chapter_framework`。
5. 校验关键字段；缺失字段写入 `missing_info[]`。
6. 用 `_shared.schemas.WritingTask` 做 pydantic 验证。
7. 把 `writing_task` 写回 `state.json`；在 `outputs/01-论文写作任务书.md` 渲染人类可读版本。
8. stdout 输出一段简短 Markdown 摘要（供调用方在对话中展示）。

## 输出

- `state.writing_task`（符合 `schemas/writing_task.schema.json`）。
- `outputs/01-论文写作任务书.md` —— 人类可读 Markdown。
- stdout —— 一段汇总摘要（含 missing_info 提示）。

详细字段定义见 `{baseDir}/references/task-book-fields.md`。

## 异常情况

- **LLM 返回非法 JSON**：Skill 自动重试 1 次；仍失败则把错误信息输出到 stderr，exit code 1。
- **关键字段缺失（blocker）**：Skill 正常 exit 0，但在 `missing_info` 中标记，等待编排层调用 `human_clarify`。
- **目标期刊未匹配**：使用 `references/journal-styles.md` 的 `default` 条目作为兜底；不会因此失败。

## Mock 模式

当 `WRITEAGENT_MOCK_LLM=1` 或未设置 `WRITEAGENT_LLM_API_KEY` 时，Skill 走 `scripts/mock.py` 提供的桩响应（针对"writing-agent-design"自指案例做了启发式匹配），可在无网络下端到端跑通流水线。
