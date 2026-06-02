# 01 · Agent 架构设计

## 一、双轨架构总图

```mermaid
flowchart TB
    user[用户自然语言需求] --> entry{运行模式}
    entry -->|本地| std[python -m agent run]
    entry -->|平台| oc[OpenClaw ReAct 大脑]

    subgraph standalone [独立模式 · LangGraph 编排]
        std --> mode{workflow or react}
        mode --> g[workflow StateGraph]
        mode --> rg[react StateGraph]
        rg --> mainAgent[Main ReAct Agent]
        mainAgent -->|delegate_to_subagent| subAgent[Dynamic Sub-agent]
        subAgent --> gateway[LLM Gateway]
        subAgent --> intermediate[state.intermediate]
        mainAgent -->|run_skill| skillCall[Skill subprocess]
        g --> n1[skill1_requirement]
        n1 -- missing_info blocker --> hc[human_clarify]
        hc --> n1
        n1 -- ok --> n2[skill2_literature]
        n2 --> n3[skill3_outline] --> n4[skill4_draft]
        n4 --> n5[skill5_format] --> n6[skill6_polish] --> ed[END]
        n1 -. error .-> rt[retry_with_fallback]
        n2 -. error .-> rt
        rt --> n1
        ckpt[("SqliteSaver checkpoints.sqlite")]
        g <--> ckpt
    end

    subgraph openclaw [OpenClaw 模式 · ReAct 自主调度]
        oc -->|扫描 SKILL.md description| oc
        oc -->|bash subprocess| call[python scripts/run.py]
    end

    subgraph skills [./skills/ 共享 Skill 层（与 LangGraph 完全解耦）]
        s1[Skill 1 run.py]
        s2[Skill 2 run.py]
        s3to6[Skill 3-6 run.py]
    end

    n1 -. subprocess .-> s1
    n2 -. subprocess .-> s2
    skillCall -. subprocess .-> s1
    skillCall -. subprocess .-> s2
    intermediate --> skills
    call --> s1 & s2 & s3to6
    skills --> state[(.writeagent/state.json + outputs/)]
    ckpt -. 旁路导出 .-> state
```

本地运行包含两种 LangGraph 模式：固定流水线位于 `agent/workflow/graph.py`
与 `agent/workflow/nodes.py`；本地 ReAct 调度位于 `agent/react/graph.py`
与 `agent/react/nodes.py`。两者共享 `agent/skill_runner.py` 的 Skill subprocess
边界。所有模型调用集中在 `agent/llm_gateway.py`；Skill script 不直接调用 LLM。

核心职责边界：

- Main Agent plans：`agent/react_runner.py` 与 `agent/react/*` 只负责规划、委派、工具调用和终止判断。
- Sub-agents reason：`agent/subagents/runtime.py` 根据 `SubAgentSpec` 动态执行临时 Sub-agent，不写固定专家类。
- Skills validate and execute：`skills/*/scripts/run.py` 读取 `state.intermediate`，执行确定性校验、增强、渲染和正式字段写入。
- LLM Gateway governs：`agent/llm_gateway.py` 统一 chat、structured JSON、repair、retry、mock 与 trace。
- State coordinates：`state.json` 协调 Main Agent、Sub-agent 与 Skill。
- Trace makes the system observable：`react_trace.json`、`subagent_trace.jsonl`、`llm_trace.jsonl` 记录全链路。

## 二、LangGraph 状态图

### 1. 状态通道（[agent/workflow/state.py](../agent/workflow/state.py)）

`WriteAgentState` 是一个 `TypedDict`，每个字段都对应 `state.schema.json`
中的顶层属性：

```python
class WriteAgentState(TypedDict, total=False):
    case_id: str
    user_request: str
    stage: str
    history: Annotated[list[HistoryEntry], operator.add]   # reducer = 列表合并

    writing_task:      NotRequired[dict[str, Any]]   # Skill 1
    literature_report: NotRequired[dict[str, Any]]   # Skill 2
    outline:           NotRequired[dict[str, Any]]   # Skill 3
    draft:             NotRequired[dict[str, Any]]   # Skill 4
    formatted_draft:   NotRequired[dict[str, Any]]   # Skill 5
    polished_draft:    NotRequired[dict[str, Any]]   # Skill 6

    error: NotRequired[str]
    retry_count: NotRequired[int]
    next_after_retry: NotRequired[str]

    workspace_root: str        # 绝对路径，用于跨 cwd 调用
    state_path: str            # 绝对路径
    references_dir: NotRequired[str]
```

`history` 字段绑定 `operator.add` reducer，使每个节点的运行记录"累加"到全局
history；其它 Skill 输出字段保持"latest-wins"语义。

### 2. 节点列表（[agent/workflow/nodes.py](../agent/workflow/nodes.py)）

| 节点名 | 类型 | 说明 |
| --- | --- | --- |
| `skill1_requirement` | Skill 节点 | 调 `skills/writing-requirement-analysis/scripts/run.py` |
| `skill2_literature` | Skill 节点 | 调 `skills/literature-review/scripts/run.py` |
| `skill3_outline` | Skill 节点 | 调 `skills/paper-outline/scripts/run.py`（待组员实现） |
| `skill4_draft` | Skill 节点 | 同上 |
| `skill5_format` | Skill 节点 | 同上 |
| `skill6_polish` | Skill 节点 | 同上 |
| `human_clarify` | 控制节点 | 当 `writing_task.missing_info` 含 blocker 时向用户提问 |
| `retry_with_fallback` | 控制节点 | 失败时回退（最多 2 次），超限后终止 |

所有 Skill 节点统一通过 `_skill_node(skill_name, ...)` 工厂构建——节点本身
极薄，业务逻辑全部在 Skill 脚本里。

### 3. 边（[agent/workflow/graph.py](../agent/workflow/graph.py)）

入口边：`START → skill1_requirement`

条件边（核心）：

- `skill1_requirement` → 
  - `human_clarify`（当 `missing_info` 含 blocker）
  - `skill2_literature`（无 blocker）
  - `retry_with_fallback`（失败 & retry_count < 2）
  - `END`（失败 & 超出重试次数）
- `human_clarify` → `skill1_requirement`
- `skill_i` → `skill_{i+1}` / retry / END
- `retry_with_fallback` → `state.next_after_retry`（即上次失败的节点名）

出口边：`skill6_polish → END`

### 4. 检查点（[agent/workflow/checkpointer.py](../agent/workflow/checkpointer.py)）

- 使用 `langgraph.checkpoint.sqlite.SqliteSaver` 把每个节点完成时的 state 写入 `.writeagent/checkpoints.sqlite`。
- 同时调用 `export_state_json` 把"对外可见"的字段镜像到 `.writeagent/state.json`，让 OpenClaw 端或外部审阅工具能直接读取。
- `resume <thread_id>` 子命令通过 SqliteSaver 在中断后无缝续跑。

## 三、SkillRunner 子进程边界

`agent/skill_runner.py` 是 LangGraph 节点与 Skill 脚本之间唯一的胶水。

设计动机：

1. **与 OpenClaw 行为一致**：OpenClaw 本质上是 `bash → python run.py`；我们用
   subprocess 模拟，保证本地能跑通 == 平台能跑通。
2. **崩溃隔离**：Skill 异常不会污染 LangGraph 进程的内存。
3. **语言无关**：未来若用 Node.js 写 Skill，只需改 `cmd[0]`，runner 本身无须改造。

调用契约：

```python
result = SkillRunner().run(
    skill_name="writing-requirement-analysis",
    state_path="C:/.../.writeagent/state.json",
    extra_args=["--user-request", "..."],
)
# result.status  in {"ok", "error"}
# result.state_after  是子进程退出后磁盘上的最新 state dict
```

子进程在启动时被注入 `PYTHONPATH=<repo>/skills`，使 `_shared.io` 与
`_shared.schemas` 能解析；这样 Skills 既不必发布成 wheel，也不必硬编码相对
import 路径。Skill 中不允许 import LLM Gateway 或 `_shared.llm`。

## 四、CLI（[agent/cli.py](../agent/cli.py)）

三个子命令：

| 命令 | 说明 |
| --- | --- |
| `python -m agent run --case <file>` | 首次跑流水线 |
| `python -m agent resume <thread_id>` | 从检查点恢复（如用户给完 `human_clarify` 答复后续跑） |
| `python -m agent inspect` | 美化展示当前 `state.json` |

默认情况下 `run` 只跑 Skill 1 → Skill 2（`--only-first-two`），因为 Skill 3-6
还是接口骨架；待第二阶段实现后改用 `--full-pipeline`。

## 五、本地实测（Gateway Mock 模式）

```powershell
> $env:WRITEAGENT_MOCK_LLM = "1"
> python -m agent run --case "case\00-用户原始需求.md" `
                      --references "case\references" `
                      --workspace ".writeagent"
┌────────────── writeAgent ──────────────┐
│ Run started  case_id=用户原始需求       │
│ workspace = .../.writeagent             │
└─────────────────────────────────────────┘
┌────────────── Run summary ─────────────┐
│ stage = skill2_done                    │
│ history (2 steps):                     │
│   - writing-requirement-analysis ok  549ms │
│   - literature-review            ok  813ms │
└─────────────────────────────────────────┘
```

两节点通过 Agent/Sub-agent 预生成 intermediate，再由 Skill subprocess 确定性落盘。
`WRITEAGENT_MOCK_LLM=1` 只作用于 `agent/llm_gateway.py`，不是 Skill 内部 mock。
在真实 LLM 下，耗时主要取决于 Main/Sub-agent 模型调用与文献数量。

## 六、与 OpenClaw 模式的对应关系

| 本地 LangGraph | OpenClaw ReAct |
| --- | --- |
| `agent/workflow/graph.py` 决定下一个节点 | OpenClaw LLM 读 SKILL.md.description 决定 |
| `agent/workflow/nodes.py` 跑 `_skill_node` | OpenClaw 直接 bash 调 `python run.py` |
| `SqliteSaver` 做检查点 | OpenClaw 自己的会话历史 |
| `human_clarify` 节点用 stdin 提问 | OpenClaw 在对话窗口提问 |
| `retry_with_fallback` 节点 | OpenClaw LLM 看到错误后自行决定 |

两套机制对**同一份 Skill 脚本**透明，开发者只需写一遍业务逻辑。
