---
name: writing-requirement-analysis
description: 论文写作需求分析与选题定位 Skill。当用户提出"写论文/任务书/选题/投稿/写作要求"时使用。本 Skill 不直接调用模型；应先由 Main Agent 派生需求分析 Sub-agent 生成 state.intermediate.requirement.raw_writing_task，再运行 scripts/run.py 校验、增强、渲染并写入 state.writing_task。
user-invocable: true
disable-model-invocation: true
homepage: https://example.org/writeagent
metadata: {"openclaw":{"requires":{"bins":["python"]}}}
---

# 写作需求分析与选题定位

把用户对"写一篇论文"的模糊请求转化为机器可消费、人类可读的**论文写作任务书**（`writing_task`），作为后续 Skill 的统一输入。

本 Skill 遵循 Agent-native 分工：

- Main Agent 判断是否需要需求分析。
- Requirement Sub-agent 读取 `user_request`、本 Skill 的 `SKILL.md`、`prompts/` 与 `references/`，生成结构化 intermediate。
- `scripts/run.py` 只执行确定性校验、增强、渲染和正式落盘。
- Skill script 不直接调用 LLM，不访问 `agent/llm_gateway.py`。

## 何时使用

满足任一条件即可触发：

- 用户提到"写论文"、"论文写作"、"投稿"、"任务书"、"选题"、"研究方向"。
- 在 writeAgent 流水线的开始阶段、`state.json` 中尚未填充 `writing_task`。
- 已有 `writing_task` 但用户明确要求"重新定位选题/调整任务书"。

## Agent 使用流程

### 1. 派生 Sub-agent

Main Agent 应先派生临时 Sub-agent，生成：

```jsonc
{
  "intermediate": {
    "requirement": {
      "raw_writing_task": {
        "topic": "...",
        "paper_type": "survey",
        "language": "zh",
        "target_journal": {"name": "未指定", "level": "未指定"},
        "word_limit": {"total": 8000},
        "core_arguments": ["..."],
        "innovation_points": [],
        "research_scope": {},
        "chapter_framework": [],
        "references_seed": [],
        "missing_info": []
      }
    }
  }
}
```

推荐 `SubAgentSpec`：

```json
{
  "role": "requirement analysis specialist",
  "task": "Convert the user request into a structured writing task draft.",
  "input_keys": ["user_request"],
  "output_key": "intermediate.requirement.raw_writing_task",
  "skill_context": ["writing-requirement-analysis"],
  "prompt_refs": ["skills/writing-requirement-analysis/prompts/extract_writing_task.md"],
  "output_schema": "WritingTask",
  "allowed_tools": ["inspect_state_subset", "read_skill_prompt", "read_skill_context"]
}
```

### 2. 运行确定性入口

```bash
python {baseDir}/scripts/run.py --state {workspace}/state.json [--user-request "..."]
```

参数：

- `--state` 必填。指向共享 `state.json`（OpenClaw 默认 `~/.openclaw/workspace/.writeagent/state.json`）。
- `--user-request` 可选。若提供则覆盖 `state.user_request`；否则从 state 中读取。

调用前置：

- `state.user_request` 必须存在。
- `state.intermediate.requirement.raw_writing_task` 必须存在并为 JSON object。

## 处理流程

1. 读取 `state.intermediate.requirement.raw_writing_task`。
2. 根据 `target_journal.name` 与 `target_journal.level` 在 `references/journal-styles.md` 中匹配风格画像（`style_profile`）。
3. 根据 `paper_type` 加载章节模板，补齐 `chapter_framework`。
4. 校验关键字段；缺失字段写入 `missing_info[]`。
5. 用 `_shared.schemas.WritingTask` 做 pydantic 验证。
6. 把正式 `writing_task` 写回 `state.json`。
7. 在 `outputs/01-论文写作任务书.md` 渲染人类可读版本。
8. stdout 输出一段简短 Markdown 摘要。

## 输出

- `state.writing_task`（符合 `schemas/writing_task.schema.json`）。
- `outputs/01-论文写作任务书.md` —— 人类可读 Markdown。
- stdout —— 一段汇总摘要（含 missing_info 提示）。

详细字段定义见 `{baseDir}/references/task-book-fields.md`。

## 异常情况

- **缺少 intermediate**：stderr 输出明确错误，exit code 1。Main Agent 应先派生 requirement analysis Sub-agent。
- **intermediate 不是 JSON object**：stderr 输出错误，exit code 1。
- **关键字段缺失（blocker）**：Skill 正常 exit 0，但在 `missing_info` 中标记，等待编排层调用 `human_clarify`。
- **目标期刊未匹配**：使用 `references/journal-styles.md` 的 `default` 条目作为兜底；不会因此失败。

## 过程知识

- `prompts/extract_writing_task.md`：供 Sub-agent 生成 raw writing task。
- `references/task-book-fields.md`：字段说明。
- `references/journal-styles.md`：期刊风格画像。
- `scripts/*.py`：Skill 内部确定性 helper，不应由 Main Agent 自由组合调用。
