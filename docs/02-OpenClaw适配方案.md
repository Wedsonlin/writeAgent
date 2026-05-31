# 02 · OpenClaw（龙虾平台）适配方案

## 一、平台能力速览

OpenClaw 是基于 AgentSkills 规范的开源个人 AI Agent 平台，与本项目相关的核心特性：

1. **Skill = 文件夹**：一个 Skill 就是 `<name>/SKILL.md` + 可选 `scripts/` /
  `references/` / `assets/`。
2. **三级加载优先级**：工作区 `./skills/` > `~/.openclaw/skills/` > 内置 Skill。
3. **ReAct 大脑**：平台内置 LLM 通过扫描各 `SKILL.md` 的 `description` 字段
  自主决策调用哪个 Skill；调用方式是 `bash → 启动` {baseDir}/scripts/...``。
4. **门控（gating）**：可在 `metadata.openclaw.requires` 声明
  `bins` / `env` / `os` / `config`，平台启动时按宿主环境自动过滤可用 Skill。
5. **斜杠命令**：`user-invocable: true` 的 Skill 会自动注册为 `/skill-name`，
  方便用户显式触发。

## 二、本项目适配总览


| 平台约束             | 本项目落地                                                                                                          |
| ---------------- | -------------------------------------------------------------------------------------------------------------- |
| 工作区 Skill 目录     | `./skills/` 下 6 个 Skill 文件夹，按平台扫描规范放置                                                                          |
| `SKILL.md` 前置元数据 | 6 份 SKILL.md 统一书写 `name`、`description`（含触发关键词）、`user-invocable: true`、`metadata.openclaw.requires.{bins, env}` |
| 调用脚本             | 统一 `python {baseDir}/scripts/run.py --state {workspace}/.writeagent/state.json [...]`                          |
| 文件 I/O           | 共享工作目录 `<workspace>/.writeagent/{state.json, inputs/, outputs/}`                                               |
| 模型调用             | OpenAI 兼容协议，统一三个环境变量 `WRITEAGENT_LLM_`*                                                                        |
| 渐进式披露            | `SKILL.md` 正文 < 200 行；详细规则下沉到 `references/`，由 LLM 按需读取                                                         |
| 依赖声明             | `requires.bins: [python]`；`requires.env: [WRITEAGENT_LLM_API_KEY]`（缺失时 Skill 被标记为 *Needs Setup*，不会崩溃）          |


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
disable-model-invocation: false
homepage: https://example.org/writeagent
metadata: {"openclaw":{"requires":{"bins":["python"],"env":["WRITEAGENT_LLM_API_KEY"]},"primaryEnv":"WRITEAGENT_LLM_API_KEY"}}
---
```

关键点：

- `metadata` **必须写成单行 JSON**（OpenClaw 的 YAML 解析器目前只支持单行）。
- `primaryEnv` 让 OpenClaw 的设置向导知道引导用户填哪个 API Key。
- `description` 直接决定 LLM 是否触发该 Skill；写法上"先做什么 + 何时触发"两段式效果最好（参见 `skills/writing-requirement-analysis/SKILL.md`）。

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

## 六、LLM 调用规范

所有 Skill 通过 `_shared.llm.chat / structured_json` 调用模型，遵循：

1. **凭证**：仅读 `WRITEAGENT_LLM_API_KEY` / `_BASE_URL` / `_MODEL`，**不**直接读 `OPENAI_API_KEY`（避免与 OpenClaw 内部其它 Skill 抢凭证）。
2. **OpenAI 兼容**：可同时支持通义千问 DashScope、智谱 GLM-4、DeepSeek、OpenAI。
3. **结构化输出**：传 `response_format={"type":"json_object"}`，并在系统提示词中复述 JSON 模式。
4. **重试**：失败按指数退避重试 3 次（4s / 8s / 16s + 随机抖动）。
5. **Mock 兜底**：环境变量 `WRITEAGENT_MOCK_LLM=1` 时全部走 `build_mock_`* 函数，不发起任何网络请求。

## 七、ReAct 调度示例

当用户在 OpenClaw 对话框输入：

> 我想写一篇 LLM Agent 的综述，目标投稿 CCF-B 中文期刊。

OpenClaw 大脑的决策序列大致如下（简化）：

1. 扫描已加载 Skill 的 `description`：触发 `writing-requirement-analysis`（命中"写论文"+"目标期刊"关键词）。
2. 调用 `bash -c "python ~/.openclaw/workspace/skills/writing-requirement-analysis/scripts/run.py --state ~/.openclaw/workspace/.writeagent/state.json --user-request '...'"`。
3. Skill 完成 → `state.writing_task` 写入；stdout 输出摘要 + Markdown 路径。
4. 大脑读到 Skill 1 的 `missing_info`：若有 `blocker`，向用户提问；否则继续。
5. 调用 `literature-review`；提示用户上传 `.bib` 或指定路径。
6. ……以此类推到 Skill 6。

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

# 2. 配置 LLM
copy .env.example .env  # 然后编辑 .env 填入凭证；或设 WRITEAGENT_MOCK_LLM=1

# 3. 模拟 OpenClaw 调用 Skill 1
python skills\writing-requirement-analysis\scripts\run.py `
    --state .writeagent\state.json `
    --user-request "想写一篇 LLM Agent 综述，CCF-B 中文期刊"

# 4. 链路上紧接 Skill 2
python skills\literature-review\scripts\run.py `
    --state .writeagent\state.json `
    --refs case\references\seed.bib `
    --citation-style "GB/T 7714"
```

第一阶段已在 Mock 模式下验证两步串联，平均耗时 < 1.5 s。

## 十、待办（第二阶段）

- 让 Skill 5（academic-formatting）的 docx/pdf 导出在 OpenClaw 沙盒中可运行（评估是否需在 `metadata.requires.bins` 增加 `pandoc`）。
- 评估在 OpenClaw 的 `installRecipe` 中声明 pip 依赖，让平台用户一键安装 `requirements-core.txt`。
- 编写 ClawHub 发布脚本（每个 Skill 单独打包，遵循"仅纯文本"约束）。

