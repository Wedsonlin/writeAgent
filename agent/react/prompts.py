"""Prompts and deterministic mock policy for the local ReAct runner."""

from __future__ import annotations

import json
from typing import Any

from .skill_registry import SkillRegistry


SYSTEM_PROMPT = """你是 writeAgent 的本地 ReAct Skill 调度大脑。

核心规则：
1. 你不能直接生成完整论文内容，具体论文写作产物必须通过 Skill 完成。
2. 你需要根据用户任务、当前 state、Skill Registry 与历史 observation 判断下一步动作。
3. 不要机械执行全部 Skill，除非用户明确要求完整论文写作流程。
4. 如果用户只要求大纲，只调用需求分析、文献梳理、大纲设计等必要 Skill。
5. 如果用户只要求润色已有初稿，优先调用润色相关 Skill；如果没有初稿，应 ask_user。
6. 如果缺少关键输入，应先 ask_user，而不是盲目执行全部 Skill。
7. 每次只能输出一个严格 JSON action，不要输出 Markdown、解释性段落或多个 action。
8. run_skill 后必须根据 observation 决定下一步。
9. 当用户需求已经满足时，调用 finish。
10. 只能对 Skill Registry 中 executable=true 的 Skill 调用 run_skill。
"""


ACTION_SCHEMA = """可用 action schema：

run_skill:
{
  "thought": "简要说明当前判断",
  "action": "run_skill",
  "action_input": {
    "skill_name": "writing-requirement-analysis",
    "reason": "需要先结构化用户写作需求"
  }
}

inspect_state:
{
  "thought": "需要查看当前共享状态",
  "action": "inspect_state",
  "action_input": {}
}

ask_user:
{
  "thought": "缺少关键输入",
  "action": "ask_user",
  "action_input": {
    "question": "请补充目标主题、目标期刊或学校格式要求。"
  }
}

finish:
{
  "thought": "已经满足用户请求",
  "action": "finish",
  "action_input": {
    "answer": "已完成所需步骤，结果已写入 state.json 和 outputs 目录。"
  }
}
"""


def build_react_messages(
    *,
    user_request: str,
    state_summary: dict[str, Any],
    skill_registry_text: str,
    steps: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Build chat messages for one ReAct decision."""
    user_prompt = "\n\n".join(
        [
            f"用户原始请求：\n{user_request}",
            f"当前 state 摘要：\n{json.dumps(state_summary, ensure_ascii=False, indent=2)}",
            f"Skill Registry：\n{skill_registry_text}",
            f"历史 observation 摘要：\n{_render_steps(steps)}",
            ACTION_SCHEMA,
            "请只输出一个严格 JSON object。",
        ]
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def build_repair_messages(raw_output: str, error: str) -> list[dict[str, str]]:
    """Ask the model to repair an invalid action into strict JSON."""
    return [
        {"role": "system", "content": "你只负责把输入修复成一个合法 JSON object。"},
        {
            "role": "user",
            "content": (
                "以下 ReAct action 不是合法 JSON 或不符合 schema。\n"
                f"错误：{error}\n"
                f"原始输出：\n{raw_output}\n\n"
                "请只输出修复后的 JSON object，不要添加 Markdown。"
            ),
        },
    ]


def build_mock_action(
    *,
    user_request: str,
    state: dict[str, Any],
    registry: SkillRegistry,
    steps: list[dict[str, Any]],
) -> str:
    """Deterministic local policy used when the shared LLM client is in mock mode."""
    executable = {spec.name for spec in registry.list_executable_specs()}
    lower = user_request.lower()
    ran_skills = [
        step.get("action_input", {}).get("skill_name")
        for step in steps
        if step.get("action") == "run_skill"
    ]

    def action(name: str, reason: str) -> str:
        return json.dumps(
            {
                "thought": reason,
                "action": "run_skill",
                "action_input": {"skill_name": name, "reason": reason},
            },
            ensure_ascii=False,
        )

    def finish(answer: str) -> str:
        return json.dumps(
            {
                "thought": "当前本地 mock 调度认为任务已经满足或已达到可执行 Skill 边界。",
                "action": "finish",
                "action_input": {"answer": answer},
            },
            ensure_ascii=False,
        )

    def ask(question: str) -> str:
        return json.dumps(
            {
                "thought": "缺少继续调度所需的关键输入。",
                "action": "ask_user",
                "action_input": {"question": question},
            },
            ensure_ascii=False,
        )

    has_draft = any(key in state for key in ("draft", "formatted_draft", "polished_draft"))
    wants_outline = any(term in lower for term in ("大纲", "outline", "章节框架"))
    wants_full = any(term in lower for term in ("完整论文", "完整", "正文", "格式化", "包含文献综述"))
    wants_polish = any(term in lower for term in ("润色", "查重", "polish", "plagiarism"))
    wants_polish_only = wants_polish and not wants_full
    vague_write = user_request.strip() in {"帮我写一篇论文。", "帮我写一篇论文", "写一篇论文"}

    last_step = steps[-1] if steps else {}
    last_observation = last_step.get("observation") or {}
    if last_observation.get("status") == "error":
        return ask(
            "刚才的 Skill 执行失败，请根据错误信息补充输入或修复 Skill 后重试。"
        )

    if wants_polish_only:
        if not has_draft:
            return ask("请提供需要润色的论文初稿，或先让系统生成 draft/formatted_draft。")
        if "polish-and-plagiarism" in executable and "polish-and-plagiarism" not in ran_skills:
            return action("polish-and-plagiarism", "用户只要求润色，应优先调用润色与查重优化 Skill。")
        return finish("已完成润色调度边界检查；当前可执行 Skill 已处理完毕。")

    if vague_write and "writing_task" not in state:
        return ask("请补充论文主题、论文类型、目标字数和格式要求。")

    if "writing_task" not in state and "writing-requirement-analysis" in executable:
        return action("writing-requirement-analysis", "需要先将用户自然语言请求转成结构化 writing_task。")

    if "literature_report" not in state and "literature-review" in executable:
        return action("literature-review", "已有 writing_task，下一步需要生成 literature_report 支撑后续写作。")

    if (wants_outline or wants_full) and "outline" not in state:
        if "paper-outline" in executable:
            return action("paper-outline", "用户需要大纲或完整论文，且已有上游信息，应生成 outline。")
        return finish("本地已完成可执行的前置 Skill；paper-outline 尚无本地入口，无法继续生成大纲。")

    if wants_full and "draft" not in state and "paper-content-generation" in executable:
        return action("paper-content-generation", "完整论文请求需要在 outline 后生成正文初稿。")

    if wants_full and "formatted_draft" not in state and "academic-formatting" in executable:
        return action("academic-formatting", "完整论文请求需要格式化初稿。")

    if wants_full and "polished_draft" not in state and "polish-and-plagiarism" in executable:
        return action("polish-and-plagiarism", "完整论文请求最后需要润色和查重优化建议。")

    if wants_outline and "outline" in state:
        return finish("已完成论文大纲生成，结果已写入 state.json 和 outputs 目录。")

    return finish("已完成当前请求所需的本地 ReAct Skill 调度。")


def _render_steps(steps: list[dict[str, Any]]) -> str:
    if not steps:
        return "暂无历史 observation。"
    compact = []
    for step in steps[-6:]:
        observation = step.get("observation", {})
        compact.append(
            {
                "step": step.get("step"),
                "thought": step.get("thought"),
                "action": step.get("action"),
                "action_input": step.get("action_input"),
                "observation": {
                    "status": observation.get("status"),
                    "skill": observation.get("skill"),
                    "produced_keys": observation.get("produced_keys"),
                    "updated_keys": observation.get("updated_keys"),
                    "stderr_tail": observation.get("stderr_tail", "")[-800:],
                    "answer": observation.get("answer"),
                },
            }
        )
    return json.dumps(compact, ensure_ascii=False, indent=2)
