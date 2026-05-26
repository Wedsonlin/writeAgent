# 示例输出 · 文献梳理报告（节选）

> 来自 Mock 模式跑 `writing-agent-design` 案例的实际产物。

## 一、研究脉络（节选）

> 2022 年 ReAct 提出工具增强范式；2023 年 LangChain、AutoGPT 推动智能体工程化；2024-2025 年 Anthropic Skills、OpenClaw 进一步把领域工作流封装为可加载模块，学术写作辅助类研究开始关注事实性与引用规范。

### LLM 智能体架构与工具调用

围绕 ReAct、工具调用、多步规划等核心机制，奠定了智能体的基础范式。

代表性文献：
- `yao2022react`
- `wang2024agentsurvey`

### Skill 化与可扩展能力体系

Anthropic Skills、OpenClaw 等机制把领域工作流封装为可加载模块，提升复用与安全。

代表性文献：
- `anthropic2025skills`
- `openclaw2025arch`

## 二、共识 · 争议 · 研究缺口

**共识：**
- 工具调用与多步规划是 LLM 智能体的核心能力。
- 可加载的 Skill / Plugin 机制有助于降低系统耦合并提升复用。

**争议：**
- Agent 应使用紧耦合的内置工具，还是开放的可扩展 Skill？
- 是否应让 LLM 直接产出最终结果，还是经多轮校验与人工审阅？

**研究缺口：**
- 面向学术写作场景的端到端 Agent 系统尚不成熟。
- 跨 Skill 的统一输入输出契约缺少公认规范。
- Agent 输出的学术规范性（引用、查重、格式）缺少自动化校验。

## 四、规范参考文献（节选）

### GB/T 7714-2015

```
[1] Yao S, Zhao J, Yu D, 等. ReAct: Synergizing Reasoning and Acting in Language Models[EB/OL]. arXiv preprint arXiv:2210.03629, 2022.
[2] Wang L, Ma C, Feng X, 等. A Survey on Large Language Model based Autonomous Agents[J]. arXiv preprint arXiv:2308.11432, 2023.
```

### APA 7

```
Yao, S., Zhao, J., Yu, D., & Du, N. (2022). ReAct: Synergizing reasoning and acting in language models. *arXiv preprint arXiv:2210.03629*.
Wang, L., Ma, C., Feng, X., & Zhang, Z. (2023). A survey on large language model based autonomous agents. *arXiv preprint arXiv:2308.11432*.
```
