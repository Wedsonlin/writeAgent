# 05 · Skill 开发规范

writeAgent 的 Skill 参考 Agent Skills 的组织方式：一个 Skill 是自包含目录，包含 Agent-readable instructions、过程知识、prompt 模板和确定性执行脚本。

## 一、核心原则

- `SKILL.md` teaches the Agent when and how to use the Skill.
- `prompts/` teaches Sub-agents how to reason.
- `references/` stores domain/process knowledge.
- `scripts/run.py` validates, formats, renders, and persists.
- Skill scripts never call LLM.

换句话说：

```text
Main Agent plans.
Sub-agents reason.
Skills validate and execute.
LLM Gateway governs.
State coordinates.
Trace makes the system observable.
```

## 二、标准目录结构

```text
skills/<skill-name>/
  SKILL.md
  prompts/
    <task_prompt>.md
  references/
    <domain_or_process_notes>.md
  assets/
    <optional_static_assets>
  scripts/
    run.py
    <deterministic_helper>.py
```

### Public Knowledge Interface

以下内容可以被 Main Agent 或 Sub-agent 读取：

- `SKILL.md`
- `prompts/*.md`
- `references/*.md`

它们用于指导 Sub-agent 生成 `state.intermediate.*`，不直接写正式产物。

### Public Execution Interface

每个可执行 Skill 必须提供：

```bash
python {baseDir}/scripts/run.py --state {workspace}/state.json
```

`run.py` 是唯一稳定执行入口，负责：

- 读取 `state.json`
- 读取对应 `state.intermediate.*`
- 执行确定性校验与转换
- 写正式产物字段
- 写 `outputs/*.md` 或其它可审阅产物
- 写 `stage` 与 `history`
- 通过 exit code 表达成功或失败

### Internal Helper Interface

`scripts/*.py` 中的其它文件是内部 deterministic helper，例如 parser、renderer、formatter、template builder。Main Agent 不应自由组合调用这些 helper。若确实需要暴露少量 helper 给 Sub-agent，必须先通过受限工具白名单和参数 schema 声明。

## 三、`SKILL.md` 写法

`SKILL.md` 应该包含：

1. YAML frontmatter。
2. Skill 的任务定位。
3. 何时使用。
4. 需要哪些 Sub-agent intermediate。
5. 推荐的 `SubAgentSpec`。
6. `scripts/run.py` 的调用方式。
7. 确定性处理流程。
8. 输出字段。
9. 异常情况。
10. 可读取的 `prompts/` 与 `references/`。

推荐 frontmatter：

```yaml
---
name: <skill-id>
description: <说明何时使用、需要哪些 intermediate、run.py 会写什么正式产物>
user-invocable: true
disable-model-invocation: true
homepage: https://example.org/writeagent
metadata: {"openclaw":{"requires":{"bins":["python"]}}}
---
```

不要在 `SKILL.md` 中写：

- Skill script 直接调用 LLM。
- Skill 需要 `WRITEAGENT_LLM_API_KEY`。
- Skill 内部有 mock LLM。
- Main Agent 可以直接写正式产物字段。

## 四、State 写入规则

Main Agent：

- 可以写 `last_runner`、`last_status` 等运行状态。
- 不直接写专业产物。

Sub-agent：

- 只能写 `state.intermediate.*`。
- 不能写 `writing_task`、`literature_report`、`outline`、`draft`、`formatted_draft`、`polished_draft`。
- 不能直接写 `outputs/`。

Skill script：

- 读取 `state.intermediate.*`。
- 执行 schema validation、确定性增强、格式化和渲染。
- 写正式产物字段和 `outputs/`。

## 五、Skill3-6 开发模板

### Skill3 · paper-outline

Sub-agent 输出：

```text
state.intermediate.outline.raw_outline
```

Skill script 输出：

```text
state.outline
outputs/03-论文大纲.md
```

### Skill4 · paper-content-generation

Sub-agent 输出：

```text
state.intermediate.draft.raw_draft
```

Skill script 输出：

```text
state.draft
outputs/04-论文初稿.md
```

### Skill5 · academic-formatting

Sub-agent 输出：

```text
state.intermediate.formatting.raw_format_report
```

Skill script 输出：

```text
state.formatted_draft
outputs/05-格式化报告.md
```

### Skill6 · polish-and-plagiarism

Sub-agent 输出：

```text
state.intermediate.polishing.raw_polish_report
```

Skill script 输出：

```text
state.polished_draft
outputs/06-润色与查重优化报告.md
```

## 六、验收要求

新增或修改 Skill 时至少满足：

- `scripts/run.py --state <state.json>` 可被 `SkillRunner` 子进程调用。
- Skill script 不 import `_shared.llm`、`agent.llm_gateway` 或任何模型调用接口。
- 缺少 required intermediate 时返回明确错误。
- 成功时写正式 state 字段、`stage`、`history` 和可审阅 output。
- 对正式输出执行 schema validation。
- `SKILL.md` 只描述 Agent/Sub-agent/Skill 的协作边界，不描述 Skill 内直接 LLM 调用。

