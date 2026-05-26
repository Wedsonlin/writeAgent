# writeAgent · 论文写作 Agent

面向学术论文写作的智能 Agent，遵循"大脑决策 + Skill 工具调用"模式，
采用 **LangGraph 编排 + OpenClaw 兼容 Skill** 的双轨架构：

- **独立模式** `python -m agent run`：LangGraph `StateGraph` 驱动 6 个 Skill 串联，
  支持检查点、断点恢复、`missing_info` 回环、失败重试。
- **OpenClaw 模式**：把 `./skills/` 整体作为工作区 Skill 安装；OpenClaw 自带
  ReAct 大脑依 `SKILL.md` 的 `description` 字段自主调度，**不依赖 LangGraph**。

两种模式共享同一份 `./skills/*/scripts/run.py` 业务实现 + 同一份 `state.json`
中间结果。

## 目录结构

```
writeAgent/
├── README.md
├── requirements-core.txt          # Skills + OpenClaw 端依赖（必装）
├── requirements-orchestrator.txt  # LangGraph 编排层增量依赖（独立模式才装）
├── .env.example                   # LLM 凭证模板
├── pyproject.toml
│
├── docs/                          # 设计文档（5 份）
│   ├── 00-总体方案与技术路线.md
│   ├── 01-Agent架构设计.md
│   ├── 02-OpenClaw适配方案.md
│   ├── 03-统一输入输出字段规范.md
│   └── 04-案例主题与执行计划.md
│
├── schemas/                       # 6 份 JSON Schema（跨 Skill 输入输出契约）
│
├── agent/                         # LangGraph 编排层（独立模式专用）
│   ├── cli.py                     # `python -m agent run|resume|inspect`
│   ├── graph.py                   # StateGraph 构建
│   ├── nodes.py                   # Skill 节点 + clarify/retry 节点
│   ├── state.py                   # TypedDict + reducer
│   ├── checkpointer.py            # SqliteSaver + state.json 旁路导出
│   ├── skill_runner.py            # 统一 subprocess 调用入口
│   ├── llm_client.py              # OpenAI 兼容客户端
│   └── prompts/
│
├── skills/                        # OpenClaw 兼容 Skill
│   ├── writing-requirement-analysis/   # Skill 1（本仓库实现）
│   ├── literature-review/              # Skill 2（本仓库实现）
│   ├── paper-outline/                  # Skill 3（接口骨架，移交张慧晴）
│   ├── paper-content-generation/       # Skill 4（接口骨架，移交张慧晴）
│   ├── academic-formatting/            # Skill 5（接口骨架，移交李泓铮）
│   ├── polish-and-plagiarism/          # Skill 6（接口骨架，移交李泓铮）
│   └── _shared/                        # 各 Skill 共享工具（llm.py、io.py、schemas.py）
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

支持任意 OpenAI 兼容端点（通义千问 DashScope、智谱 GLM、DeepSeek 等）。
无 Key 时设 `WRITEAGENT_MOCK_LLM=1` 可走桩函数离线跑通流程。

### 3. 运行案例（独立模式）

```powershell
# 从内置案例（writing-agent-design）跑 Skill 1 → Skill 2
python -m agent run --case case/00-用户原始需求.md

# 查看当前 state
python -m agent inspect

# 从最近检查点恢复
python -m agent resume
```

### 4. 部署到 OpenClaw

将 `skills/` 文件夹整体复制（或软链接）到 `~/.openclaw/workspace/skills/`，
重启 OpenClaw 后即可通过 `/writing-requirement-analysis`、`/literature-review`
等斜杠命令触发，或让 OpenClaw 的 ReAct 大脑自动调度。详见
[docs/02-OpenClaw适配方案.md](docs/02-OpenClaw适配方案.md)。


## 协作合约

- 所有 Skill 共享 `./schemas/*.schema.json` 定义的字段
- 所有 Skill 通过 `python {baseDir}/scripts/run.py --state <path>` 调用，输入输出均落 `state.json`
- 详见 [docs/03-统一输入输出字段规范.md](docs/03-统一输入输出字段规范.md)
