"""Generate a chapter_framework list based on paper_type.

Each template is a 5-9 chapter scaffold typical for that genre. The orchestrator
later refines word budgets in Skill 3 (paper-outline), so we only allocate
rough proportions here.
"""

from __future__ import annotations

from typing import Any


_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "survey": [
        {"chapter_id": "1", "title": "引言", "key_points": ["研究背景", "研究意义", "本文贡献"]},
        {"chapter_id": "2", "title": "相关概念与定义", "key_points": ["核心术语", "分类框架"]},
        {"chapter_id": "3", "title": "代表性方法与系统", "key_points": ["按聚类分类介绍代表性工作"]},
        {"chapter_id": "4", "title": "对比分析", "key_points": ["从多维度对比代表性工作"]},
        {"chapter_id": "5", "title": "应用场景", "key_points": ["落地案例与效果"]},
        {"chapter_id": "6", "title": "挑战与未来方向", "key_points": ["研究缺口", "可行思路"]},
        {"chapter_id": "7", "title": "结论", "key_points": ["总结要点", "展望"]},
    ],
    "empirical": [
        {"chapter_id": "1", "title": "引言", "key_points": ["研究问题", "研究假设", "贡献"]},
        {"chapter_id": "2", "title": "相关工作", "key_points": ["既有研究综述"]},
        {"chapter_id": "3", "title": "研究方法", "key_points": ["数据集", "实验设计", "评测指标"]},
        {"chapter_id": "4", "title": "实验结果", "key_points": ["主实验", "消融", "敏感性分析"]},
        {"chapter_id": "5", "title": "讨论", "key_points": ["发现解释", "威胁有效性"]},
        {"chapter_id": "6", "title": "结论", "key_points": ["主要发现", "未来工作"]},
    ],
    "theoretical": [
        {"chapter_id": "1", "title": "引言", "key_points": ["问题陈述", "动机", "贡献"]},
        {"chapter_id": "2", "title": "预备知识", "key_points": ["符号约定", "基础概念"]},
        {"chapter_id": "3", "title": "理论模型", "key_points": ["核心定义", "关键定理", "证明思路"]},
        {"chapter_id": "4", "title": "性质与扩展", "key_points": ["推论", "边界条件", "鲁棒性"]},
        {"chapter_id": "5", "title": "示例与应用", "key_points": ["典型案例分析"]},
        {"chapter_id": "6", "title": "讨论", "key_points": ["与已有理论对比", "局限"]},
        {"chapter_id": "7", "title": "结论", "key_points": ["总结", "展望"]},
    ],
    "system": [
        {"chapter_id": "1", "title": "引言", "key_points": ["背景", "面临的挑战", "本文贡献"]},
        {"chapter_id": "2", "title": "相关工作", "key_points": ["既有系统综述与对比"]},
        {"chapter_id": "3", "title": "系统设计", "key_points": ["总体架构", "核心模块", "数据流"]},
        {"chapter_id": "4", "title": "关键技术实现", "key_points": ["核心算法", "工程优化"]},
        {"chapter_id": "5", "title": "实验与评测", "key_points": ["实验设置", "性能与效果"]},
        {"chapter_id": "6", "title": "案例应用", "key_points": ["典型案例与效果展示"]},
        {"chapter_id": "7", "title": "讨论", "key_points": ["局限与改进方向"]},
        {"chapter_id": "8", "title": "结论", "key_points": ["总结", "未来工作"]},
    ],
    "case_study": [
        {"chapter_id": "1", "title": "引言", "key_points": ["案例背景", "研究问题"]},
        {"chapter_id": "2", "title": "相关工作", "key_points": ["既有研究综述"]},
        {"chapter_id": "3", "title": "案例介绍", "key_points": ["对象描述", "数据采集"]},
        {"chapter_id": "4", "title": "分析与发现", "key_points": ["定性/定量分析", "主要发现"]},
        {"chapter_id": "5", "title": "讨论", "key_points": ["对实践的启示"]},
        {"chapter_id": "6", "title": "结论", "key_points": ["总结", "推广性"]},
    ],
    "position": [
        {"chapter_id": "1", "title": "引言与立场", "key_points": ["立场陈述", "研究意义"]},
        {"chapter_id": "2", "title": "现状梳理", "key_points": ["既有观点", "争议焦点"]},
        {"chapter_id": "3", "title": "论证", "key_points": ["核心论点", "支持证据"]},
        {"chapter_id": "4", "title": "反驳与回应", "key_points": ["可能反对意见", "回应"]},
        {"chapter_id": "5", "title": "结论与呼吁", "key_points": ["总结", "对学界呼吁"]},
    ],
}


def build_chapter_framework(paper_type: str, total_words: int) -> list[dict[str, Any]]:
    """Build a chapter_framework list, distributing word budget by simple weights."""
    template = _TEMPLATES.get(paper_type) or _TEMPLATES["survey"]
    weights = _weights_for(paper_type, len(template))
    framework: list[dict[str, Any]] = []
    for chapter, weight in zip(template, weights):
        budget = max(300, int(round(total_words * weight)))
        framework.append({**chapter, "word_budget": budget})
    return framework


def _weights_for(paper_type: str, n: int) -> list[float]:
    if paper_type == "survey":
        weights = [0.08, 0.10, 0.30, 0.20, 0.12, 0.12, 0.08]
    elif paper_type == "empirical":
        weights = [0.10, 0.15, 0.25, 0.30, 0.13, 0.07]
    elif paper_type == "theoretical":
        weights = [0.10, 0.10, 0.30, 0.20, 0.12, 0.10, 0.08]
    elif paper_type == "system":
        weights = [0.08, 0.10, 0.20, 0.22, 0.15, 0.12, 0.08, 0.05]
    elif paper_type == "case_study":
        weights = [0.10, 0.15, 0.25, 0.25, 0.15, 0.10]
    elif paper_type == "position":
        weights = [0.15, 0.20, 0.30, 0.20, 0.15]
    else:
        weights = [1.0 / n] * n
    # Align to length
    if len(weights) != n:
        weights = (weights + [1.0 / n] * n)[:n]
    s = sum(weights)
    return [w / s for w in weights]
