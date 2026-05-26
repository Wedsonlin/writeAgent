# 示例输出 · 论文写作任务书

> 来自 Mock 模式跑 `面向学术论文写作的智能 Agent 设计与实现` 案例的实际产物。
> 真实模式下结构相同，内容由 LLM 生成。

```json
{
  "topic": "面向学术论文写作的智能 Agent 设计与实现",
  "paper_type": "system",
  "language": "zh",
  "target_journal": {
    "name": "计算机研究与发展",
    "level": "CCF-B",
    "style_profile": {
      "citation_style": "GB/T 7714",
      "tone": "formal-zh",
      "structure_hint": "摘要(中英)-引言-相关工作-方法-实验-讨论-结论-参考文献"
    }
  },
  "word_limit": {"total": 10000},
  "core_arguments": [
    "大脑决策 + Skill 工具调用模式可显著降低学术写作门槛",
    "统一输入输出字段是多 Skill 协作的关键保障",
    "LangGraph 与 OpenClaw 双轨编排可兼顾本地开发与平台部署"
  ],
  "innovation_points": [
    "提出 LangGraph 编排 + OpenClaw 兼容 Skill 的双轨架构",
    "以 JSON Schema 作为跨 Skill 契约的统一基线",
    "针对论文写作场景设计了 6 个层次清晰的 Skill 划分"
  ],
  "chapter_framework": [
    {"chapter_id": "1", "title": "引言", "key_points": ["背景", "面临的挑战", "本文贡献"], "word_budget": 800},
    {"chapter_id": "2", "title": "相关工作", "key_points": ["既有系统综述与对比"], "word_budget": 1000},
    {"chapter_id": "3", "title": "系统设计", "key_points": ["总体架构", "核心模块", "数据流"], "word_budget": 2000},
    {"chapter_id": "4", "title": "关键技术实现", "key_points": ["核心算法", "工程优化"], "word_budget": 2200},
    {"chapter_id": "5", "title": "实验与评测", "key_points": ["实验设置", "性能与效果"], "word_budget": 1500},
    {"chapter_id": "6", "title": "案例应用", "key_points": ["典型案例与效果展示"], "word_budget": 1200},
    {"chapter_id": "7", "title": "讨论", "key_points": ["局限与改进方向"], "word_budget": 800},
    {"chapter_id": "8", "title": "结论", "key_points": ["总结", "未来工作"], "word_budget": 500}
  ],
  "missing_info": [
    {
      "field": "word_limit.by_chapter",
      "question": "是否对各章节有具体字数预算？",
      "criticality": "nice-to-have",
      "suggested_default": "由 Skill 3 按比例分配"
    }
  ]
}
```
