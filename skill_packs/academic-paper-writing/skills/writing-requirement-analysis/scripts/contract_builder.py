from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


SKILL_ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = Path(__file__).resolve().parents[3]
INPUT_SCHEMA_PATH = SKILL_ROOT / "references" / "contracts" / "input.schema.json"
LOCAL_WRITING_TASK_SCHEMA_PATH = SKILL_ROOT / "references" / "contracts" / "writing-task.schema.json"
PACK_WRITING_TASK_SCHEMA_PATH = PACK_ROOT / "schemas" / "writing_task.schema.json"
JOURNAL_PROFILE_PATH = SKILL_ROOT / "references" / "contracts" / "journal" / "ccf-b-profiles.yaml"


@dataclass
class ContractError(Exception):
    message: str
    missing_fields: list[str]

    def __str__(self) -> str:
        return self.message


def build_writing_task_payload(data: dict[str, Any], output_path: str | Path | None = None) -> dict[str, Any]:
    _validate_schema(data, _load_json(INPUT_SCHEMA_PATH), "input")
    brief = _expect_mapping(data.get("argument_brief"), "argument_brief")
    missing = _critical_missing_fields(data, brief)
    if missing:
        raise ContractError("writing requirement input is missing critical argument brief fields", missing)

    venue = _expect_mapping(brief.get("venue"), "argument_brief.venue")
    word_limit = _word_limit(venue)
    topic = _topic(data, brief)
    section_plan = brief.get("section_plan") or _default_sections(str(venue.get("paper_type")))
    target_journal, profile_matched = _target_journal(venue)

    writing_task = {
        "topic": topic,
        "paper_type": str(venue["paper_type"]),
        "language": str(venue["language"]),
        "target_journal": target_journal,
        "word_limit": word_limit,
        "core_arguments": _string_list(brief.get("core_arguments") or brief.get("contributions")),
        "innovation_points": _string_list(brief.get("innovation_points") or brief.get("contributions")),
        "research_scope": _research_scope(brief),
        "chapter_framework": [_chapter(chapter) for chapter in section_plan if isinstance(chapter, dict)],
        "references_seed": _reference_seed(data),
        "missing_info": [],
    }
    _validate_schema(writing_task, _load_json(LOCAL_WRITING_TASK_SCHEMA_PATH), "writing_task")
    _validate_schema(writing_task, _load_json(PACK_WRITING_TASK_SCHEMA_PATH), "writing_task")

    markdown = _render_task_book(writing_task)
    markdown_path = str(Path(output_path).with_suffix(".md")) if output_path is not None else ""
    return {
        "artifact_type": "writing_task",
        "writing_task": writing_task,
        "task_book_markdown": markdown,
        "task_book_markdown_path": markdown_path,
        "quality_checks": {
            "required_fields_confirmed": True,
            "journal_profile_matched": profile_matched,
            "task_book_rendered": bool(markdown.strip()),
        },
    }


def _critical_missing_fields(data: dict[str, Any], brief: dict[str, Any]) -> list[str]:
    venue = brief.get("venue") if isinstance(brief.get("venue"), dict) else {}
    scope = brief.get("scope") if isinstance(brief.get("scope"), dict) else {}
    checks = {
        "argument_brief.topic": brief.get("topic") or data.get("topic"),
        "argument_brief.core_claim": brief.get("core_claim"),
        "argument_brief.core_arguments": brief.get("core_arguments"),
        "argument_brief.contributions": brief.get("contributions"),
        "argument_brief.venue.paper_type": venue.get("paper_type"),
        "argument_brief.venue.journal_or_level": venue.get("journal") or venue.get("name") or venue.get("level"),
        "argument_brief.venue.word_limit": venue.get("word_limit"),
        "argument_brief.venue.language": venue.get("language"),
        "argument_brief.scope.boundary": scope.get("boundary"),
        "references_seed": data.get("references_seed"),
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
    raw = venue.get("word_limit")
    try:
        total = int(raw.get("total") if isinstance(raw, dict) else raw)
    except (TypeError, ValueError):
        raise ContractError("word_limit must be a positive integer", ["argument_brief.venue.word_limit"]) from None
    if total <= 0:
        raise ContractError("word_limit must be a positive integer", ["argument_brief.venue.word_limit"])
    return {"total": total, "by_chapter": None, "chapter_allocation_stage": "paper_outline"}


def _target_journal(venue: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    name = str(venue.get("journal") or venue.get("name") or "未指定期刊")
    level = str(venue.get("level") or "unspecified")
    matched_profile = _profile_from_yaml(name, level)
    style_profile = matched_profile or venue.get("style_profile")
    if not isinstance(style_profile, dict):
        style_profile = _style_profile(name, level)
    return {"name": name, "level": level, "style_profile": style_profile}, matched_profile is not None


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
        "word_budget": None,
        "depends_on": chapter.get("depends_on"),
    }


def _reference_seed(data: dict[str, Any]) -> list[dict[str, Any]]:
    seeds = data.get("references_seed") or []
    if not isinstance(seeds, list):
        return []
    return [seed for seed in seeds if isinstance(seed, dict)]


def _default_sections(paper_type: str) -> list[dict[str, Any]]:
    if paper_type != "system":
        titles = ["引言", "相关工作", "研究设计", "分析与讨论", "结论"]
        points = [["背景", "问题"], ["研究脉络"], ["方法或框架"], ["论证与讨论"], ["总结", "未来工作"]]
    else:
        titles = ["引言", "相关工作", "系统设计", "关键技术实现", "实验与评测", "案例应用", "讨论", "结论"]
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
    return [
        {"chapter_id": str(index + 1), "title": title, "key_points": points[index], "word_budget": None, "depends_on": None}
        for index, title in enumerate(titles)
    ]


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


def _profile_from_yaml(name: str, level: str) -> dict[str, str] | None:
    profiles = (_load_yaml(JOURNAL_PROFILE_PATH).get("profiles") or []) if JOURNAL_PROFILE_PATH.exists() else []
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        match = profile.get("match") if isinstance(profile.get("match"), dict) else {}
        if match.get("name_contains") and str(match["name_contains"]) in name:
            return dict(profile.get("style_profile") or {})
        if match.get("level_prefix") and level.upper().startswith(str(match["level_prefix"]).upper()):
            return dict(profile.get("style_profile") or {})
    return None


def _render_task_book(task: dict[str, Any]) -> str:
    journal = task["target_journal"]
    style = journal["style_profile"]
    word_limit = task["word_limit"]
    lines = [
        f"# 论文写作任务书 · {task['topic']}",
        "",
        "## 一、基本信息",
        "",
        f"- 主题：{task['topic']}",
        f"- 论文类型：{task['paper_type']}",
        f"- 写作语言：{task['language']}",
        f"- 目标期刊：{journal['name']}（级别：{journal['level']}）",
        f"- 期刊风格：引用 `{style.get('citation_style')}` · 语气 `{style.get('tone')}` · 结构提示：{style.get('structure_hint')}",
        f"- 总字数：{word_limit['total']}",
        "- 章节字数分配：由 `paper_outline` 阶段完成",
        "",
        "## 二、研究范围",
        "",
        f"- 研究领域：{task['research_scope'].get('domain', '')}",
        "- 子方向：",
    ]
    lines.extend(f"  - {topic}" for topic in task["research_scope"].get("subtopics", []))
    lines.extend(
        [
            f"- 范围边界：{task['research_scope'].get('boundary', '')}",
            "",
            "## 三、核心论点与创新点",
            "",
        ]
    )
    lines.extend(f"{index}. {argument}" for index, argument in enumerate(task["core_arguments"], start=1))
    lines.extend(["", "**创新点：**"])
    lines.extend(f"- {point}" for point in task["innovation_points"])
    lines.extend(
        [
            "",
            "## 四、候选章节框架",
            "",
            "| 章节 | 标题 | 核心要点 |",
            "| --- | --- | --- |",
        ]
    )
    for chapter in task["chapter_framework"]:
        points = "；".join(chapter.get("key_points", []))
        lines.append(f"| {chapter.get('chapter_id')} | {chapter.get('title')} | {points} |")
    lines.extend(["", "## 五、初始参考文献种子", ""])
    for seed in task["references_seed"]:
        lines.append(f"- [{seed.get('type', 'reference')}] id=`{seed.get('id', '')}` path=`{seed.get('path', '')}`")
    lines.extend(["", "## 六、待确认信息", "", "- 无；关键写作信息已在需求分析阶段确认。"])
    return "\n".join(lines).strip() + "\n"


def _validate_schema(data: dict[str, Any], schema: dict[str, Any], label: str) -> None:
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda error: list(error.path))
    if not errors:
        return
    fields = [_schema_error_field(error, label) for error in errors]
    raise ContractError(f"{label} does not match schema", fields)


def _schema_error_field(error: Any, label: str) -> str:
    path = ".".join(str(part) for part in error.path)
    if error.validator == "required":
        match = re.match(r"'([^']+)' is a required property", error.message)
        if match:
            return f"{path}.{match.group(1)}" if path else match.group(1)
    return path or label


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}
