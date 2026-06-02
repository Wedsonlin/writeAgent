# writeAgent · 论文写作 Agent

面向学术论文写作的智能 Agent，遵循"Main Agent 规划 + 动态 Sub-agent 推理 + Skill 确定性执行"模式，采用 **固定 workflow + 本地 ReAct + OpenClaw 兼容 Skill** 的多轨架构：

- **workflow mode** `python -m agent run --mode workflow`：LangGraph `StateGraph` 驱动固定 Skill pipeline，用于端到端回归测试、课堂演示和稳定复现，支持检查点、断点恢复、`missing_info` 回环、失败重试。
- **react mode** `python -m agent run --mode react`：独立的 LangGraph ReAct `StateGraph` 读取 `SKILL.md` / Skill Registry，由 Main Agent 输出严格 JSON action。复杂认知任务通过 `delegate_to_subagent` 动态派生临时 Sub-agent，Sub-agent 写 `state.intermediate`，再由 Skill script 校验、渲染和落盘。
- **OpenClaw 模式**：把 `./skills/` 整体作为工作区 Skill 安装；OpenClaw 自带ReAct 大脑依 `SKILL.md` 的 `description` 字段自主调度，**不依赖 LangGraph**。

这些模式共享同一份 `./skills/*/scripts/run.py` 业务实现 + 同一份 `state.json`。workflow mode 是固定流程回归测试层；react mode 是本地 Agent-native 调试层。Skill script 不直接调用 LLM，也不生成专业认知内容，只读取 `state.intermediate` 并执行 schema validation、确定性增强、格式化、渲染和正式字段写入。

架构原则：

- Main Agent plans.
- Sub-agents reason.
- Skills validate and execute.
- LLM Gateway governs.
- State coordinates.
- Trace makes the system observable.

## 目录结构

```
writeAgent/
├── README.md
├── requirements-core.txt          # Skills + OpenClaw 端依赖（必装）
├── requirements-orchestrator.txt  # LangGraph 编排层增量依赖（独立模式才装）
├── .env.example                   # LLM 凭证模板
├── pyproject.toml
│
├── docs/                          # 设计文档（6 份）
│   ├── 00-总体方案与技术路线.md
│   ├── 01-Agent架构设计.md
│   ├── 02-OpenClaw适配方案.md
│   ├── 03-统一输入输出字段规范.md
│   ├── 04-案例主题与执行计划.md
│   └── 05-Skill开发规范.md
│
├── schemas/                       # 6 份 JSON Schema（跨 Skill 输入输出契约）
│
├── agent/                         # 本地编排层（workflow + react）
│   ├── cli.py                     # `python -m agent run|resume|inspect`
│   ├── workflow_runner.py         # 固定 workflow 入口封装
│   ├── react_runner.py            # LangGraph ReAct StateGraph 入口
│   ├── llm_gateway.py             # 唯一模型调用治理层
│   ├── state_store.py             # state.json 读写 / intermediate 写入
│   ├── trace_store.py             # react/subagent/llm trace 写入
│   ├── a2a/                       # 轻量 A2A-like 委派协议
│   ├── subagents/                 # SubAgentFactory / Runtime / policy / tools
│   ├── workflow/                  # 固定 LangGraph 流水线
│   │   ├── graph.py               # StateGraph 构建
│   │   ├── nodes.py               # Skill 节点 + clarify/retry 节点
│   │   ├── state.py               # TypedDict + reducer
│   │   ├── checkpointer.py        # SqliteSaver + state.json 旁路导出
│   │   └── prompt.py              # 编排层提示词（SYSTEM / CLARIFY / RETRY）
│   ├── react/                     # ReAct graph / nodes / state / registry / tools / prompts / types
│   └── skill_runner.py            # 统一 subprocess 调用入口
│
├── skills/                        # OpenClaw 兼容 Skill
│   ├── writing-requirement-analysis/   # Skill 1（本仓库实现）
│   ├── literature-review/              # Skill 2（本仓库实现）
│   ├── paper-outline/                  # Skill 3（接口骨架）
│   ├── paper-content-generation/       # Skill 4（接口骨架）
│   ├── academic-formatting/            # Skill 5（接口骨架）
│   ├── polish-and-plagiarism/          # Skill 6（接口骨架）
│   └── _shared/                        # 各 Skill 共享确定性工具（io.py、schemas.py）
│
├── case/                          # 案例素材与阶段产物
│   ├── 00-用户原始需求.md
│   ├── 01-论文写作任务书.{json,md}
│   ├── 02-文献梳理报告.{json,md}
│   └── references/seed.bib
│
├── tests/
└── examples/
```

## 快速上手

### 1. 安装依赖

```powershell
# 完整安装（独立模式所需）
python -m pip install -r requirements-orchestrator.txt

# 或：仅安装 Skill 端依赖（OpenClaw 部署场景）
python -m pip install -r requirements-core.txt
```

### 2. 配置 LLM

```powershell
copy .env.example .env
# 编辑 .env，填入 WRITEAGENT_LLM_API_KEY / BASE_URL / MODEL
```

支持任意 OpenAI 兼容端点（通义千问 DashScope、智谱 GLM、DeepSeek 等）。所有模型调用都通过 `agent/llm_gateway.py`，Main Agent 与 Sub-agent 调用都会写入 `llm_trace.jsonl`。Skill script 内禁止直接调用模型。
无 Key 时设 `WRITEAGENT_MOCK_LLM=1` 可走 Gateway mock 离线跑通流程。

### 3. 运行案例（本地模式）

```powershell
# workflow mode：固定 LangGraph / pipeline 工作流，用于回归测试与稳定演示
python -m agent run --mode workflow --case case/00-用户原始需求.md
python -m agent run --mode workflow --request "请写一篇关于生成式 AI 辅助论文写作的论文"

# react mode：Main ReAct Agent + 动态 Sub-agent 委派
python -m agent run --mode react --request "请先生成一份关于生成式 AI 辅助论文写作的论文大纲"

# 查看当前 state
python -m agent inspect

# 从最近检查点恢复（workflow mode 专用）
python -m agent resume
```

默认 `python -m agent run` 仍等价于 `--mode workflow`，用于固定流程回归。react mode 运行结束后会打印每一步 action / observation 摘要，并写出：

- `<workspace>/react_trace.json`：Main Agent 每一步 action / observation。
- `<workspace>/subagent_trace.jsonl`：每个动态 Sub-agent 的委派 spec、状态与结果。
- `<workspace>/llm_trace.jsonl`：Main Agent 与 Sub-agent 的模型调用记录。

### 4. 部署到 OpenClaw

将 `skills/` 文件夹整体复制（或软链接）到 `~/.openclaw/workspace/skills/`，
重启 OpenClaw 后即可通过 `/writing-requirement-analysis`、`/literature-review`
等斜杠命令触发，或让 OpenClaw 的 ReAct 大脑自动调度。详见 [docs/02-OpenClaw适配方案.md](docs/02-OpenClaw适配方案.md)。

## 协作合约

- 所有 Skill 共享 `./schemas/*.schema.json` 定义的字段
- 所有 Skill 通过 `python {baseDir}/scripts/run.py --state <path>` 调用，输入输出均落 `state.json`
- Main Agent 不直接写专业产物；Sub-agent 只能写 `state.intermediate.*`
- Skill script 不直接调用 LLM，不 import `agent.llm_gateway` 或 `_shared.llm`
- 详见 [docs/03-统一输入输出字段规范.md](docs/03-统一输入输出字段规范.md)

