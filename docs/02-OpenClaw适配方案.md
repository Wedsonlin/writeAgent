# 02 · OpenClaw（龙虾平台）适配方案

## 一、平台能力速览

OpenClaw 是基于 AgentSkills 规范的开源个人 AI Agent 平台，与本项目相关的核心特性：

1. **Skill = 文件夹**：一个 Skill 就是 `<name>/SKILL.md` + 可选 `scripts/` /
  `references/` / `assets/`。
2. **三级加载优先级**：工作区 `./skills/` > `~/.openclaw/skills/` > 内置 Skill。
3. **ReAct 大脑**：平台内置 LLM 通过扫描各 `SKILL.md` 的 `description` 与正文 instructions
  自主决策使用哪个 Skill；正式落盘仍通过 `bash → python {baseDir}/scripts/run.py` 完成。
4. **门控（gating）**：可在 `metadata.openclaw.requires` 声明
  `bins` / `env` / `os` / `config`，平台启动时按宿主环境自动过滤可用 Skill。
5. **斜杠命令**：`user-invocable: true` 的 Skill 会自动注册为 `/skill-name`，
  方便用户显式触发。

## 二、本项目适配总览


| 平台约束             | 本项目落地                                                                                                          |
| ---------------- | -------------------------------------------------------------------------------------------------------------- |
| 工作区 Skill 目录     | `./skills/` 下 6 个 Skill 文件夹，按平台扫描规范放置                                                                          |
| `SKILL.md` 前置元数据 | 6 份 SKILL.md 统一书写 `name`、`description`（含触发关键词与 intermediate 要求）、`user-invocable: true`、`disable-model-invocation: true` |
| 调用脚本             | 统一 `python {baseDir}/scripts/run.py --state {workspace}/.writeagent/state.json [...]`                          |
| 文件 I/O           | 共享工作目录 `<workspace>/.writeagent/{state.json, inputs/, outputs/}`                                               |
| 模型调用             | 不在 Skill subprocess 中发生；由 OpenClaw Agent runtime 或本地 `agent/llm_gateway.py` 负责                                |
| 渐进式披露            | `SKILL.md` 正文写 Agent instructions；详细规则下沉到 `prompts/` 与 `references/`，由 Sub-agent 按需读取                    |
| 依赖声明             | `requires.bins: [python]`；Skill 级 metadata 不声明 LLM API Key                                                           |


## 三、目录布局映射

```
本仓库                                       OpenClaw 安装后
writeAgent/skills/                            ~/.openclaw/workspace/skills/
├── writing-requirement-analysis/             ├── writing-requirement-analysis/
│   ├── SKILL.md                              │   ├── SKILL.md
│   ├── scripts/                              │   ├── scripts/
│   ├── references/                           │   ├── references/
│   └── assets/                               │   └── assets/
├── literature-review/                        ├── literature-review/
│   └── ...                                   │   └── ...
├── paper-outline/  (接口骨架)                ├── paper-outline/
├── paper-content-generation/                 ├── paper-content-generation/
├── academic-formatting/                      ├── academic-formatting/
├── polish-and-plagiarism/                    ├── polish-and-plagiarism/
└── _shared/                                  └── _shared/   # 共享工具，对外不直接调用
```

**安装方式（任选其一）：**

1. 工作区拷贝：`cp -r writeAgent/skills/* ~/.openclaw/workspace/skills/`
2. 符号链接（推荐开发期）：`ln -s "$PWD/skills/writing-requirement-analysis" ~/.openclaw/workspace/skills/writing-requirement-analysis`
3. ClawHub 发布（远期）：把每个 Skill 上传到 ClawHub，他人通过 `clawhub install <slug>` 安装。

## 四、SKILL.md 写法约定

所有 6 份 `SKILL.md` 共用同一套元数据模板：

```yaml
---
name: <skill-id>
description: <一句话能力描述 + 何时触发，必须包含中文触发关键词如"任务书/文献综述/大纲/初稿/格式/润色">
user-invocable: true
disable-model-invocation: true
homepage: https://example.org/writeagent
metadata: {"openclaw":{"requires":{"bins":["python"]}}}
---
```

关键点：

- `metadata` **必须写成单行 JSON**（OpenClaw 的 YAML 解析器目前只支持单行）。
- `description` 直接决定 Agent 是否触发该 Skill；写法上应同时说明触发条件、required intermediate、正式输出字段。
- `disable-model-invocation: true` 表示 Skill subprocess 不直接调用模型；模型推理由 OpenClaw Agent runtime 或本地 Sub-agent 处理。
- `SKILL.md` 正文应包含推荐 `SubAgentSpec`、`prompts/` 引用和 `scripts/run.py` 调用方式。

## 五、文件 I/O 与工作目录

OpenClaw 会把 Skill 安装到 `~/.openclaw/workspace/skills/<name>/`。本项目约定：


| 路径                                                     | 用途                                |
| ------------------------------------------------------ | --------------------------------- |
| `~/.openclaw/workspace/.writeagent/state.json`         | 跨 Skill 状态                        |
| `~/.openclaw/workspace/.writeagent/inputs/`            | 用户上传的 .bib / .pdf                 |
| `~/.openclaw/workspace/.writeagent/outputs/`           | 各 Skill 渲染的 Markdown / docx / pdf |
| `~/.openclaw/workspace/.writeagent/checkpoints.sqlite` | 仅在用户也启用本地 LangGraph 时存在           |


每个 Skill 自始至终通过 `_shared.io.resolve_workspace(args.state)` 解析路径，
对平台或本地差异完全透明。

## 六、模型调用边界

本项目的 Skill 遵循 Anthropic-like Agent Skills 分层：Skill 是 instructions + resources + deterministic scripts，不是独立 LLM caller。

1. **Main Agent / OpenClaw Agent runtime**：读取 `SKILL.md`，决定是否需要派生专业 Sub-agent。
2. **Sub-agent**：读取 `SKILL.md`、`prompts/`、`references/`，通过平台模型能力或本地 `agent/llm_gateway.py` 生成 `state.intermediate.*`。
3. **Skill script**：只读取 intermediate，做 deterministic validation / formatting / rendering / persistence。
4. **本地模式**：所有模型调用必须经过 `agent/llm_gateway.py`，并写入 `llm_trace.jsonl`。
5. **OpenClaw 模式**：不需要 import 本仓库的 `SkillRunner`；平台可以按 `SKILL.md` 中的命令直接启动 `scripts/run.py`。

## 七、ReAct 调度示例

当用户在 OpenClaw 对话框输入：

> 我想写一篇 LLM Agent 的综述，目标投稿 CCF-B 中文期刊。

OpenClaw 大脑的决策序列大致如下（简化）：

1. 扫描已加载 Skill 的 `description`：触发 `writing-requirement-analysis`（命中"写论文"+"目标期刊"关键词）。
2. 读取 `SKILL.md` 与 `prompts/extract_writing_task.md`，派生 requirement Sub-agent。
3. Sub-agent 写入 `state.intermediate.requirement.raw_writing_task`。
4. 调用 `bash -c "python ~/.openclaw/workspace/skills/writing-requirement-analysis/scripts/run.py --state ~/.openclaw/workspace/.writeagent/state.json"`。
5. Skill 完成 → `state.writing_task` 写入；stdout 输出摘要 + Markdown 路径。
6. 若 `missing_info` 有 blocker，Agent 向用户提问；否则继续派生 literature analysis / synthesis Sub-agent。
7. 调用 `literature-review` 的 `scripts/run.py` 组装正式 `literature_report`。

整个调度过程**不需要任何 LangGraph**——这正是双轨架构的精妙之处。

## 八、文件类型支持

OpenClaw 对 Skill 内文件类型有限制（仅纯文本可上传到 ClawHub），本项目策略：

- **BibTeX / Markdown / YAML**：原生纯文本，全部可入仓。
- **PDF**：不入 Skill 包，而是放到 `.writeagent/inputs/` 作为用户运行时数据。
- **DOCX / 字体文件**（Skill 5）：放在 `assets/` 但仅本仓使用，发布到 ClawHub 时由组员 3 改成下载脚本或链接。

## 九、最小可运行（MVP）冒烟测试

```powershell
# 1. 安装核心依赖（OpenClaw 端足够）
python -m pip install -r requirements-core.txt

# 2. 通过本地 Agent/Sub-agent 链路生成 intermediate 并调用 Skill1/2
python examples\run_skill1_then_skill2.py

# 3. 或使用 react mode 验证 Main Agent → Sub-agent → Skill
python -m agent run --mode react --request "我只需要一份关于 EMI 技术用于 CFRP 损伤检测的论文详细大纲。"
```

第一阶段已验证 Sub-agent → Skill1 → Sub-agent → Skill2 串联。Skill subprocess 不直接调用 LLM。

## 十、待办（第二阶段）

- 让 Skill 5（academic-formatting）的 docx/pdf 导出在 OpenClaw 沙盒中可运行（评估是否需在 `metadata.requires.bins` 增加 `pandoc`）。
- 评估在 OpenClaw 的 `installRecipe` 中声明 pip 依赖，让平台用户一键安装 `requirements-core.txt`。
- 编写 ClawHub 发布脚本（每个 Skill 单独打包，遵循"仅纯文本"约束）。

