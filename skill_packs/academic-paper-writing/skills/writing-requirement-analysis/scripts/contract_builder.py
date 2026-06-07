from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ContractError(Exception):
    message: str
    missing_fields: list[str]

    def __str__(self) -> str:
        return self.message


def build_writing_task_payload(data: dict[str, Any]) -> dict[str, Any]:
    brief = _expect_mapping(data.get("argument_brief"), "argument_brief")
    missing = _critical_missing_fields(brief)
    if missing:
        raise ContractError("writing requirement input is missing critical argument brief fields", missing)

    venue = _expect_mapping(brief.get("venue"), "argument_brief.venue")
    word_limit = _word_limit(venue)
    topic = _topic(data, brief)
    section_plan = brief.get("section_plan") or _default_sections(str(venue.get("paper_type")), word_limit["total"])
    target_journal = _target_journal(venue)

    writing_task = {
        "topic": topic,
        "paper_type": str(venue["paper_type"]),
        "language": str(venue.get("language") or "zh"),
        "target_journal": target_journal,
        "word_limit": word_limit,
        "core_arguments": _string_list(brief.get("core_arguments") or brief.get("contributions")),
        "innovation_points": _string_list(brief.get("innovation_points") or brief.get("contributions")),
        "research_scope": _research_scope(brief),
        "chapter_framework": [_chapter(chapter) for chapter in section_plan if isinstance(chapter, dict)],
        "references_seed": _reference_seed(data),
        "missing_info": _missing_info(word_limit),
    }
    return {"artifact_type": "writing_task", "writing_task": writing_task}


def _critical_missing_fields(brief: dict[str, Any]) -> list[str]:
    venue = brief.get("venue") if isinstance(brief.get("venue"), dict) else {}
    checks = {
        "argument_brief.core_claim": brief.get("core_claim"),
        "argument_brief.contributions": brief.get("contributions"),
        "argument_brief.venue.paper_type": venue.get("paper_type"),
        "argument_brief.venue.journal": venue.get("journal") or venue.get("name"),
    }
    return [field for field, value in checks.items() if _is_empty(value)]


def _expect_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{field} must be an object", [field])
    return value


def _topic(data: dict[str, Any], brief: dict[str, Any]) -> str:
    explicit = brief.get("topic") or data.get("topic")
    if explicit:
        return str(explicit)
    contribution_name = brief.get("contribution_name")
    if contribution_name:
        return str(contribution_name)
    core_claim = str(brief.get("core_claim", "")).strip()
    for prefix in ("本文表明，", "本文表明:", "本文表明：", "本文表明"):
        if core_claim.startswith(prefix):
            core_claim = core_claim[len(prefix) :].strip()
    return core_claim[:120] or "未命名论文主题"


def _word_limit(venue: dict[str, Any]) -> dict[str, Any]:
    raw = venue.get("word_limit", 8000)
    if isinstance(raw, dict):
        total = int(raw.get("total") or 8000)
        by_chapter = raw.get("by_chapter")
    else:
        total = int(raw)
        by_chapter = None
    return {"total": total, "by_chapter": by_chapter}


def _target_journal(venue: dict[str, Any]) -> dict[str, Any]:
    name = str(venue.get("journal") or venue.get("name") or "未指定期刊")
    level = str(venue.get("level") or "unspecified")
    style_profile = venue.get("style_profile")
    if not isinstance(style_profile, dict):
        style_profile = _style_profile(name, level)
    return {"name": name, "level": level, "style_profile": style_profile}


def _style_profile(name: str, level: str) -> dict[str, str]:
    if "计算机研究与发展" in name:
        return {
            "citation_style": "GB/T 7714",
            "tone": "formal-zh",
            "structure_hint": "摘要(中英)-引言-相关工作-方法-实验-讨论-结论-参考文献",
        }
    if level.upper().startswith("CCF"):
        return {
            "citation_style": "GB/T 7714",
            "tone": "formal-zh",
            "structure_hint": "摘要-引言-相关工作-方法-实验-讨论-结论-参考文献",
        }
    return {"citation_style": "GB/T 7714", "tone": "formal-zh", "structure_hint": "按目标期刊模板调整"}


def _research_scope(brief: dict[str, Any]) -> dict[str, Any]:
    scope = brief.get("scope") if isinstance(brief.get("scope"), dict) else {}
    return {
        "domain": str(scope.get("domain") or ""),
        "subtopics": _string_list(scope.get("subtopics")),
        "boundary": str(scope.get("boundary") or ""),
    }


def _chapter(chapter: dict[str, Any]) -> dict[str, Any]:
    return {
        "chapter_id": str(chapter.get("chapter_id") or chapter.get("id") or ""),
        "title": str(chapter.get("title") or ""),
        "key_points": _string_list(chapter.get("key_points")),
        "word_budget": int(chapter.get("word_budget") or 0),
        "depends_on": chapter.get("depends_on"),
    }


def _reference_seed(data: dict[str, Any]) -> list[dict[str, Any]]:
    seeds = data.get("references_seed") or []
    if not isinstance(seeds, list):
        return []
    return [seed for seed in seeds if isinstance(seed, dict)]


def _missing_info(word_limit: dict[str, Any]) -> list[dict[str, str]]:
    if word_limit.get("by_chapter") is not None:
        return []
    return [
        {
            "field": "word_limit.by_chapter",
            "question": "是否对各章节有具体字数预算（如引言 1500 / 方法 3000 ...）？",
            "criticality": "nice-to-have",
            "suggested_default": "由 Skill 3 按比例分配",
        }
    ]


def _default_sections(paper_type: str, total_words: int) -> list[dict[str, Any]]:
    if paper_type != "system":
        titles = ["引言", "相关工作", "研究设计", "分析与讨论", "结论"]
        ratios = [0.12, 0.18, 0.28, 0.30, 0.12]
        points = [["背景", "问题"], ["研究脉络"], ["方法或框架"], ["论证与讨论"], ["总结", "未来工作"]]
    else:
        titles = ["引言", "相关工作", "系统设计", "关键技术实现", "实验与评测", "案例应用", "讨论", "结论"]
        ratios = [0.08, 0.10, 0.20, 0.22, 0.15, 0.12, 0.08, 0.05]
        points = [
            ["背景", "面临的挑战", "本文贡献"],
            ["既有系统综述与对比"],
            ["总体架构", "核心模块", "数据流"],
            ["核心算法", "工程优化"],
            ["实验设置", "性能与效果"],
            ["典型案例与效果展示"],
            ["局限与改进方向"],
            ["总结", "未来工作"],
        ]
    budgets = _allocate(total_words, ratios)
    return [
        {"chapter_id": str(index + 1), "title": title, "key_points": points[index], "word_budget": budgets[index], "depends_on": None}
        for index, title in enumerate(titles)
    ]


def _allocate(total_words: int, ratios: list[float]) -> list[int]:
    budgets = [int(total_words * ratio / 100) * 100 for ratio in ratios]
    budgets[-1] += total_words - sum(budgets)
    return budgets


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if item is not None and str(item)]
    return [str(value)]


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return len(value) == 0
    return False
