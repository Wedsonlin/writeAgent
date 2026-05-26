"""LLM prompts for literature-review."""

from __future__ import annotations

import json
from textwrap import dedent
from typing import Any


# --------------------------------------------------------------------------- #
# Per-paper claim extraction
# --------------------------------------------------------------------------- #


EXTRACT_SYSTEM = dedent(
    """
    你是一位文献综述助手。给定一篇论文的元数据与（可选）摘要，请抽取：
    1. 该论文的核心观点（key_claims），1-3 条，每条 ≤ 50 字。
    2. 证据强度（evidence_strength）：strong / moderate / weak / anecdotal。
       - strong：含理论证明或大规模可复现实验；
       - moderate：含中小规模实验或可重复的案例研究；
       - weak：仅含定性分析或单个案例；
       - anecdotal：观点性或经验性陈述。
    严格输出 JSON：{"key_claims": [...], "evidence_strength": "..."}。
    不输出任何额外文字，不使用 Markdown。
    """
).strip()


def build_extract_messages(paper: dict[str, Any]) -> list[dict[str, str]]:
    snippet = {
        "title": paper.get("title", ""),
        "authors": paper.get("authors", []),
        "year": paper.get("year", 0),
        "venue": paper.get("venue", ""),
        "abstract": (paper.get("abstract") or "")[:1500],
    }
    return [
        {"role": "system", "content": EXTRACT_SYSTEM},
        {
            "role": "user",
            "content": "论文元数据：\n" + json.dumps(snippet, ensure_ascii=False, indent=2),
        },
    ]


def build_extract_mock(paper: dict[str, Any]) -> dict[str, Any]:
    title = (paper.get("title") or "").lower()
    if "agent" in title or "tool" in title or "react" in title:
        return {
            "key_claims": [
                "提出了基于 LLM 的智能体框架，能够调用工具完成多步任务。",
                "在多项基准上显著优于不使用工具的基线方法。",
            ],
            "evidence_strength": "moderate",
        }
    if "survey" in title or "review" in title or "综述" in title:
        return {
            "key_claims": [
                "系统梳理了相关领域研究脉络与代表性方法。",
                "总结了当前主要挑战与未来研究方向。",
            ],
            "evidence_strength": "moderate",
        }
    if "skill" in title or "openclaw" in title.lower():
        return {
            "key_claims": [
                "提出 Skill 化能力扩展机制，支持低耦合工具集成。",
            ],
            "evidence_strength": "weak",
        }
    return {
        "key_claims": [paper.get("title", "（无摘要）")[:50] or "未提取到核心观点"],
        "evidence_strength": "weak",
    }


# --------------------------------------------------------------------------- #
# Cross-paper synthesis
# --------------------------------------------------------------------------- #


SYNTHESIS_SYSTEM = dedent(
    """
    你是资深研究综述者。我会给你：
    1. `core_arguments`：本文要论证的核心论点列表。
    2. `papers`：已抽取 key_claims 的文献列表（每条含 id / title / authors / year / venue / key_claims / evidence_strength）。

    请输出严格的 JSON，包含以下字段：
    {
      "clusters": [{ "name": "...", "summary": "...", "paper_ids": [...] }, ...],
      "timeline_summary": "...",
      "consensus": ["...", ...],
      "controversies": ["...", ...],
      "research_gaps": ["...", ...],
      "alignments": [{ "paper_id": "...", "core_argument_index": 0,
                       "stance": "supports|extends|challenges|neutral",
                       "note": "..." }, ...]
    }

    要求：
    - 聚类数 3-6 个；每个聚类至少 2 篇 paper；聚类名要能体现主题。
    - timeline_summary 50-100 字，按时间维度叙述领域演进。
    - consensus / controversies / research_gaps 各 2-5 条，简短一句话。
    - alignments：每篇 paper 至少给出 1 条与某个 core_argument 的对齐关系。
    - 不输出任何额外文字、不使用 Markdown 代码块。
    """
).strip()


def build_synthesis_messages(
    core_arguments: list[str], papers: list[dict[str, Any]]
) -> list[dict[str, str]]:
    compact_papers = [
        {
            "id": p["id"],
            "title": p.get("title", ""),
            "authors": p.get("authors", [])[:3],
            "year": p.get("year", 0),
            "venue": p.get("venue", ""),
            "key_claims": p.get("key_claims", []),
            "evidence_strength": p.get("evidence_strength", "weak"),
        }
        for p in papers
    ]
    user_payload = {
        "core_arguments": core_arguments,
        "papers": compact_papers,
    }
    return [
        {"role": "system", "content": SYNTHESIS_SYSTEM},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, indent=2)},
    ]


def build_synthesis_mock(
    core_arguments: list[str], papers: list[dict[str, Any]]
) -> dict[str, Any]:
    """Deterministic offline synthesis used in mock mode.

    The strategy is intentionally simple — split papers into three buckets by
    topical hints in the title — so the output is reproducible and the schema
    contract is exercised even without a network connection.
    """
    bucket_arch: list[dict[str, Any]] = []
    bucket_skill: list[dict[str, Any]] = []
    bucket_writing: list[dict[str, Any]] = []
    bucket_other: list[dict[str, Any]] = []
    for p in papers:
        title = (p.get("title") or "").lower()
        if any(k in title for k in ("agent", "react", "tool", "planning", "multi-agent")):
            bucket_arch.append(p)
        elif any(k in title for k in ("skill", "openclaw", "plugin", "anthropic", "spec")):
            bucket_skill.append(p)
        elif any(k in title for k in ("writing", "academic", "scholarly", "scientific", "literature", "survey")):
            bucket_writing.append(p)
        else:
            bucket_other.append(p)

    clusters: list[dict[str, Any]] = []
    if bucket_arch:
        clusters.append(
            {
                "name": "LLM 智能体架构与工具调用",
                "summary": "围绕 ReAct、工具调用、多步规划等核心机制，奠定了智能体的基础范式。",
                "paper_ids": [p["id"] for p in bucket_arch],
            }
        )
    if bucket_skill:
        clusters.append(
            {
                "name": "Skill 化与可扩展能力体系",
                "summary": "Anthropic Skills、OpenClaw 等机制把领域工作流封装为可加载模块，提升复用与安全。",
                "paper_ids": [p["id"] for p in bucket_skill],
            }
        )
    if bucket_writing:
        clusters.append(
            {
                "name": "学术写作辅助与文献综述",
                "summary": "利用 LLM 辅助学术写作、文献综述生成与知识抽取，关注事实性与可控性。",
                "paper_ids": [p["id"] for p in bucket_writing],
            }
        )
    if bucket_other:
        clusters.append(
            {
                "name": "其他相关工作",
                "summary": "覆盖评测、提示工程、检索增强等支撑性研究。",
                "paper_ids": [p["id"] for p in bucket_other],
            }
        )

    alignments: list[dict[str, Any]] = []
    for p in papers:
        title = (p.get("title") or "").lower()
        idx, stance, note = 0, "supports", "提供基础范式支撑。"
        if any(k in title for k in ("skill", "openclaw")):
            idx = 0
            stance = "supports"
            note = "印证 Skill 化能力扩展可有效降低耦合。"
        elif any(k in title for k in ("schema", "json", "spec")):
            idx = 1 if len(core_arguments) > 1 else 0
            stance = "supports"
            note = "支持以统一字段约束作为多 Skill 协作基线。"
        elif any(k in title for k in ("langchain", "langgraph", "workflow")):
            idx = 2 if len(core_arguments) > 2 else 0
            stance = "extends"
            note = "提供编排框架的实现参考。"
        alignments.append(
            {
                "paper_id": p["id"],
                "core_argument_index": idx,
                "stance": stance,
                "note": note,
            }
        )

    timeline_summary = (
        "2022 年 ReAct 提出工具增强范式；2023 年 LangChain、AutoGPT 推动智能体工程化；"
        "2024-2025 年 Anthropic Skills、OpenClaw 进一步把领域工作流封装为可加载模块，"
        "学术写作辅助类研究开始关注事实性与引用规范。"
    )

    return {
        "clusters": clusters,
        "timeline_summary": timeline_summary,
        "consensus": [
            "工具调用与多步规划是 LLM 智能体的核心能力。",
            "可加载的 Skill / Plugin 机制有助于降低系统耦合并提升复用。",
        ],
        "controversies": [
            "Agent 应使用紧耦合的内置工具，还是开放的可扩展 Skill？",
            "是否应让 LLM 直接产出最终结果，还是经多轮校验与人工审阅？",
        ],
        "research_gaps": [
            "面向学术写作场景的端到端 Agent 系统尚不成熟。",
            "跨 Skill 的统一输入输出契约缺少公认规范。",
            "Agent 输出的学术规范性（引用、查重、格式）缺少自动化校验。",
        ],
        "alignments": alignments,
    }
