# 01 · Agent 架构设计

## 一、双轨架构总图

```mermaid
flowchart TB
    user[用户自然语言需求] --> entry{运行入口}
    entry -->|本地| cli[python -m agent run]
    entry -->|平台| oc[OpenClaw ReAct 大脑]

    subgraph local [本地模式 · LangChain ReAct 调度]
        cli --> reactGraph[ReAct StateGraph]
        reactGraph --> mainAgent[Main Agent bind_tools]
        mainAgent -->|AIMessage.tool_calls: delegate_to_subagent| subAgent[SubAgent ReAct Graph]
        mainAgent -->|AIMessage.tool_calls: run_skill| skillCall[Skill subprocess]
        subAgent --> gateway[LLM Gateway]
        subAgent --> stateJson[(state.json)]
        skillCall --> stateJson
        trace[react_trace + subagent_trace + llm_trace]
        mainAgent --> trace
        subAgent --> trace
    end

    subgraph openclaw [OpenClaw 模式 · ReAct 自主调度]
        oc -->|扫描 SKILL.md description| oc
        oc -->|bash subprocess| call[python scripts/run.py]
    end

    subgraph skills [./skills/ 共享 Skill 层]
        s1[Skill 1 run.py]
        s2[Skill 2 run.py]
        s3to6[Skill 3-6 run.py]
    end

    skillCall -. subprocess .-> s1
    skillCall -. subprocess .-> s2
    call --> s1 & s2 & s3to6
    skills --> outputs[(state.json + outputs/)]
```

本地运行使用 LangChain-native ReAct 调度：`agent/react_runner.py` 构建运行上下文，
`agent/react/graph.py` 与 `agent/react/nodes.py` 负责 `ChatModel.bind_tools(...)` 循环和工具调用。
模型配置沿用 `agent/llm_gateway.py`，实际 ChatModel 创建集中在 `agent/react/model_factory.py`；Skill script 不直接调用 LLM。

核心职责边界：

- Main Agent plans：`agent/react_runner.py` 与 `agent/react/*` 负责规划、委派、工具调用和终止判断。
- Sub-agents reason：`agent/subagents/runtime.py` 根据 `SubAgentSpec` 委托 `agent/react/subagent_graph.py` 动态执行受限 SubAgent ReAct graph。
- Skills validate and execute：`skills/*/scripts/run.py` 执行确定性校验、增强、渲染和正式字段写入。
- LLM Gateway governs：`agent/llm_gateway.py` 统一配置、mock 与 trace；Agent 决策主路径使用 LangChain ChatModel tool-calling。
- State coordinates：`state.json` 协调 Main Agent、Sub-agent 与 Skill。
- Trace makes the system observable：`react_trace.json`、`subagent_trace.jsonl`、`llm_trace.jsonl` 记录全链路。

## 二、ReAct 状态图

### 1. 状态通道（[agent/react/state.py](../agent/react/state.py)）

`MainAgentState` 是本地 ReAct 循环的 LangGraph channel，包含消息历史、用户请求、工作区路径、Skill Registry 文本、已执行 tool call、运行状态和最终回答。

主要字段：

```python
class MainAgentState(TypedDict, total=False):
    messages: Annotated[list[Any], add_messages]
    user_request: str
    workspace_root: str
    state_path: str
    trace_path: str
    registry_text: str
    step_count: int
    max_steps: int
    steps: list[dict[str, Any]]
    status: Literal["running", "finished", "ask_user", "error", "max_steps_exceeded"]
    answer: str
```

### 2. 节点列表（[agent/react/nodes.py](../agent/react/nodes.py)）

| 节点名 | 说明 |
| --- | --- |
| `main_agent` | 调用 `model.bind_tools(main_tools)` 后的 ChatModel，接收 `AIMessage.tool_calls` 或最终自然语言回答 |
| `main_tools` | 执行 `inspect_state / run_skill / delegate_to_subagent / ask_user`，把 JSON 字符串结果作为 `ToolMessage` 返回 |

### 3. Tool 合约

Main Agent 可调用的 LangChain tools 包括：

| tool | 说明 |
| --- | --- |
| `inspect_state` | 摘要查看当前 `state.json` |
| `delegate_to_subagent` | 为认知型任务生成结构化中间材料 |
| `run_skill` | 通过 `SkillRunner` 调用 `skills/<name>/scripts/run.py` |
| `ask_user` | 信息不足时向用户提问 |

没有 `finish` 工具。任务完成时，模型返回无 tool calls 的最终 `AIMessage`。`max_steps` 防止无限循环；运行结束后写出 `react_trace.json`。

## 三、SkillRunner 子进程边界

`agent/skill_runner.py` 是本地 ReAct 与 Skill 脚本之间的胶水。

设计动机：

1. **与 OpenClaw 行为一致**：OpenClaw 本质上是 `bash -> python run.py`；本地也用 subprocess 模拟。
2. **崩溃隔离**：Skill 异常不会污染 ReAct 进程内存。
3. **语言无关**：未来若用 Node.js 写 Skill，只需扩展 runner 命令选择，调度层无需理解业务实现。

调用契约：

```python
result = SkillRunner().run(
    skill_name="writing-requirement-analysis",
    state_path="C:/.../.writeagent/state.json",
    extra_args=["--user-request", "..."],
)
# result.status in {"ok", "error"}
# result.state_after 是子进程退出后磁盘上的最新 state dict
```

子进程启动时注入 `PYTHONPATH=<repo>/skills`，使 `_shared.io` 与
`_shared.schemas` 能解析；Skills 既不必发布成 wheel，也不必硬编码相对
import 路径。Skill 中不允许 import LLM Gateway 或 `_shared.llm`。

## 四、CLI（[agent/cli.py](../agent/cli.py)）

两个子命令：

| 命令 | 说明 |
| --- | --- |
| `python -m agent run --case <file>` | 运行本地 ReAct 调度 |
| `python -m agent inspect` | 美化展示当前 `state.json` |

常用参数：

- `--request`：直接传入用户请求。
- `--workspace`：指定 `.writeagent` 工作目录。
- `--references`：指定参考文献目录。
- `--max-steps`：限制 ReAct 决策步数。

## 五、本地实测（Gateway Mock 模式）

```powershell
> $env:WRITEAGENT_MOCK_LLM = "1"
> python -m agent run --case "case/00-用户原始需求.md" `
                      --references "case/references" `
                      --workspace ".writeagent"
┌────────────── writeAgent ──────────────┐
│ Run started  mode=langchain-react      │
│ workspace = .../.writeagent            │
└────────────────────────────────────────┘
┌──────────── ReAct run summary ─────────┐
│ [1] delegate_to_subagent status=ok     │
│ [1] run_skill status=ok                │
│ Final status: finished                 │
│ State path: .../.writeagent/state.json │
└────────────────────────────────────────┘
```

`WRITEAGENT_MOCK_LLM=1` 只作用于 `agent/llm_gateway.py`，不是 Skill 内部 mock。
在真实 LLM 下，耗时主要取决于 Main/Sub-agent 模型调用与文献数量。

## 六、与 OpenClaw 模式的对应关系

| 本地 ReAct | OpenClaw ReAct |
| --- | --- |
| `agent/react/graph.py` 运行 LangChain tool-calling 决策循环 | OpenClaw 自带 ReAct 大脑运行决策循环 |
| `agent/react/nodes.py` 提供本地工具 | OpenClaw 提供平台工具 |
| `SkillRunner` subprocess 调 `python run.py` | OpenClaw 直接 bash 调 `python run.py` |
| `react_trace.json` / `subagent_trace.jsonl` / `llm_trace.jsonl` | OpenClaw 自己的会话历史与日志 |

两套机制对同一份 Skill 脚本透明，开发者只需写一遍业务逻辑。
