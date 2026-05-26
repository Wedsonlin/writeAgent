"""LLM prompt templates for writing-requirement-analysis."""

from __future__ import annotations

import json
from textwrap import dedent
from typing import Any


SYSTEM_PROMPT = dedent(
    """
    你是一位资深的学术写作教练，擅长把研究者模糊的写作意图迅速结构化为一份
    论文写作任务书。你严格只输出合法 JSON 对象（response_format=json_object），
    不输出任何额外文字、不使用 Markdown 代码块。

    JSON 必须严格符合下述模式（字段缺失则填 null 或空数组；数值字段保持类型；
    枚举字段必须取给定值之一）：

    {schema_summary}

    抽取规则：
    1. `topic` 必须用一句完整的话概括论文主题。
    2. `paper_type` 在 survey / empirical / theoretical / system / case_study /
       position 中选一个最贴近的；若用户写"综述/review"→survey，"系统/平台/实现"→system，
       "实验/对照实验/实证"→empirical，"提出新算法/新理论模型"→theoretical。
    3. `target_journal.name` 若用户未指定，填 "未指定"。`level` 优先依据用户原文（CCF A/B/C、
       SCI、中文核心）；未指定则填 "未指定"。
    4. `word_limit.total` 必须 ≥ 1000；用户未指定时按 paper_type 给合理默认：survey 8000、
       empirical 6000、theoretical 8000、system 9000、case_study 5000、position 4000。
    5. `core_arguments` 至少 1 条，每条不超过 60 字。
    6. `chapter_framework` 暂时留空数组（章节模板由后处理填充）。
    7. `missing_info` 标出 "blocker | important | nice-to-have" 三档。常见 blocker：
       目标期刊未指定且用户没有给级别画像、字数未给且 paper_type 无法推断、核心论点为空。
    8. `language` 默认 "zh"；若用户全程用英文请求或明确要求英文输出，填 "en"。
    """
).strip()


USER_PROMPT_TEMPLATE = dedent(
    """
    以下是用户的原始写作需求。请抽取出符合上述模式的 JSON 对象。

    ===== 用户需求开始 =====
    {user_request}
    ===== 用户需求结束 =====

    若用户提到了具体的参考文献清单（BibTeX 文件路径、PDF 文件路径或文献名称片段），
    请把它们放入 `references_seed` 数组，并尽量给出 type=`bibtex`/`pdf`/`text`/`url` 的判断。
    """
).strip()


def _schema_summary() -> str:
    """Compact schema description that's small enough to embed in the prompt."""
    summary = {
        "topic": "string",
        "paper_type": "enum(survey|empirical|theoretical|system|case_study|position)",
        "language": "enum(zh|en|bilingual)",
        "target_journal": {
            "name": "string",
            "level": "enum(CCF-A|CCF-B|CCF-C|SCI|EI|中文核心|未指定|其他)",
        },
        "word_limit": {"total": "integer >= 1000", "by_chapter": "object<string, integer> | null"},
        "core_arguments": "array<string> (>=1)",
        "innovation_points": "array<string>",
        "research_scope": {"domain": "string", "subtopics": "array<string>", "boundary": "string"},
        "chapter_framework": "array  # leave empty, will be filled by template",
        "references_seed": "array<{id,type,path?,raw?}>",
        "missing_info": "array<{field,question,criticality(enum),suggested_default?}>",
    }
    return json.dumps(summary, ensure_ascii=False, indent=2)


def build_messages(user_request: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(schema_summary=_schema_summary()),
        },
        {"role": "user", "content": USER_PROMPT_TEMPLATE.format(user_request=user_request)},
    ]


def build_mock_payload(user_request: str) -> dict[str, Any]:
    """Heuristic offline payload for the self-referential case study.

    The check is intentionally fuzzy so that small wording changes in the
    user request still trigger the right mock. For arbitrary inputs we fall
    back to a generic survey-on-LLM-agents skeleton.
    """
    lower = user_request.lower()
    is_writing_agent = (
        "写作 agent" in user_request
        or "写作agent" in user_request
        or "writing agent" in lower
        or "论文写作" in user_request
    )
    if is_writing_agent:
        return _mock_writing_agent_case()
    return _mock_generic_llm_survey()


def _mock_writing_agent_case() -> dict[str, Any]:
    return {
        "topic": "面向学术论文写作的智能 Agent 设计与实现",
        "paper_type": "system",
        "language": "zh",
        "target_journal": {
            "name": "计算机研究与发展",
            "level": "CCF-B",
        },
        "word_limit": {"total": 10000, "by_chapter": None},
        "core_arguments": [
            "大脑决策 + Skill 工具调用模式可显著降低学术写作门槛",
            "统一输入输出字段是多 Skill 协作的关键保障",
            "LangGraph 与 OpenClaw 双轨编排可兼顾本地开发与平台部署",
        ],
        "innovation_points": [
            "提出 LangGraph 编排 + OpenClaw 兼容 Skill 的双轨架构",
            "以 JSON Schema 作为跨 Skill 契约的统一基线",
            "针对论文写作场景设计了 6 个层次清晰的 Skill 划分",
        ],
        "research_scope": {
            "domain": "大语言模型 Agent · 学术写作辅助 · 工具编排",
            "subtopics": [
                "需求结构化与选题定位",
                "文献梳理与引用规范",
                "大纲生成与正文撰写",
                "格式校验与语言润色",
            ],
            "boundary": "不讨论模型本身的预训练与微调；不评测查重服务",
        },
        "chapter_framework": [],
        "references_seed": [
            {"id": "seed-bib", "type": "bibtex", "path": "case/references/seed.bib"}
        ],
        "missing_info": [
            {
                "field": "word_limit.by_chapter",
                "question": "是否对各章节有具体字数预算（如引言 1500 / 方法 3000 ...）？",
                "criticality": "nice-to-have",
                "suggested_default": "由 Skill 3 按比例分配",
            }
        ],
    }


def _mock_generic_llm_survey() -> dict[str, Any]:
    return {
        "topic": "大语言模型驱动的智能 Agent 研究综述",
        "paper_type": "survey",
        "language": "zh",
        "target_journal": {"name": "未指定", "level": "未指定"},
        "word_limit": {"total": 8000, "by_chapter": None},
        "core_arguments": [
            "LLM Agent 的核心能力源自工具调用与规划",
            "多 Agent 协作是未来研究方向",
        ],
        "innovation_points": [],
        "chapter_framework": [],
        "references_seed": [],
        "missing_info": [
            {
                "field": "target_journal.name",
                "question": "目标投稿期刊或会议是？",
                "criticality": "blocker",
                "suggested_default": "中文核心 / 计算机研究与发展",
            },
            {
                "field": "innovation_points",
                "question": "您希望在论文中突出哪些创新点或贡献？",
                "criticality": "important",
                "suggested_default": "结合分类框架与代表性系统的对比分析",
            },
        ],
    }
