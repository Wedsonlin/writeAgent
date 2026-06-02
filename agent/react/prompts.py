"""Prompts and deterministic mock policy for the local ReAct runner."""

from __future__ import annotations

import json
from typing import Any

from .skill_registry import SkillRegistry


SYSTEM_PROMPT = """你是 Main ReAct Agent，负责全局规划、任务分派、工具调用、状态检查和最终验收。

核心约束：
1. 你不应该直接完成复杂专业认知任务，包括文献观点提取、研究脉络综合、论文大纲生成、正文长篇撰写、学术润色、查重降重改写、格式规范校验说明生成。
2. 当任务需要专业理解、长文本生成、结构化抽取、综合分析、改写或评价时，必须优先使用 delegate_to_subagent 派生临时 Sub-agent。
3. Sub-agent 只产出 state.intermediate 下的结构化 intermediate；Skill script 负责校验、格式化、渲染和正式产物落盘。
4. 你可以直接做的事情仅限于判断下一步动作、检查 state、决定是否调用 Skill script、决定是否派生 Sub-agent、提出用户补充信息问题、总结最终状态。
5. 不要机械执行全部 Skill。只有用户明确要求完整论文生成时才执行完整链路。
6. 如果用户只要求大纲，不要调用正文生成、格式化和润色 Skill。
7. 如果用户只要求润色，不要从需求分析开始完整重跑；若没有初稿，应 ask_user。
8. 每次只能输出一个严格 JSON action，不要输出 Markdown、解释性段落或多个 action。
9. run_skill 只能在对应 intermediate 已经存在或用户已有正式输入时调用。
10. 只能对 Skill Registry 中 executable=true 的 Skill 调用 run_skill。
"""


ACTION_SCHEMA = """可用 action schema：

delegate_to_subagent:
{
  "thought": "专业分析或生成任务需要临时 Sub-agent 完成",
  "action": "delegate_to_subagent",
  "action_input": {
    "role": "requirement analysis specialist",
    "task": "Convert the user request into a structured writing task draft.",
    "input_keys": ["user_request"],
    "output_key": "intermediate.requirement.raw_writing_task",
    "skill_context": ["writing-requirement-analysis"],
    "prompt_refs": ["skills/writing-requirement-analysis/prompts/extract_writing_task.md"],
    "output_schema": "WritingTask",
    "allowed_tools": ["inspect_state_subset", "read_skill_prompt", "read_skill_context"],
    "success_criteria": ["The output must be valid structured JSON."],
    "constraints": {
      "max_steps": 3,
      "max_context_chars": 30000,
      "can_delegate": false,
      "write_scope": "intermediate_only"
    },
    "model_policy": {
      "temperature": 0.2,
      "max_tokens": 6000
    }
  }
}

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
    delegated_outputs = [
        step.get("action_input", {}).get("output_key")
        for step in steps
        if step.get("action") == "delegate_to_subagent"
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

    def delegate(
        *,
        role: str,
        task: str,
        input_keys: list[str],
        output_key: str,
        skill_context: list[str],
        prompt_refs: list[str],
        output_schema: str,
        reason: str,
        allowed_tools: list[str] | None = None,
    ) -> str:
        return json.dumps(
            {
                "thought": reason,
                "action": "delegate_to_subagent",
                "action_input": {
                    "role": role,
                    "task": task,
                    "input_keys": input_keys,
                    "output_key": output_key,
                    "skill_context": skill_context,
                    "prompt_refs": prompt_refs,
                    "output_schema": output_schema,
                    "allowed_tools": allowed_tools
                    or ["inspect_state_subset", "read_skill_prompt", "read_skill_context"],
                    "success_criteria": ["The output must be valid structured JSON."],
                    "constraints": {
                        "max_steps": 3,
                        "max_context_chars": 30000,
                        "can_delegate": False,
                        "write_scope": "intermediate_only",
                        "require_output_schema": True,
                        "allow_file_write": False,
                    },
                    "model_policy": {"temperature": 0.2, "max_tokens": 6000},
                },
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
    if last_observation.get("status") == "failed":
        return ask("刚才的 Sub-agent 执行失败，请检查 delegation spec、权限或补充输入后重试。")

    if wants_polish_only:
        if not has_draft:
            return ask("请提供需要润色的论文初稿，或先让系统生成 draft/formatted_draft。")
        if not _has_path(state, "intermediate.polishing.raw_polish_report") and "intermediate.polishing.raw_polish_report" not in delegated_outputs:
            return delegate(
                role="academic polishing specialist",
                task="Analyze the existing draft and produce structured polishing and plagiarism-reduction suggestions.",
                input_keys=["draft", "formatted_draft", "polished_draft"],
                output_key="intermediate.polishing.raw_polish_report",
                skill_context=["polish-and-plagiarism"],
                prompt_refs=["skills/polish-and-plagiarism/prompts/polish.md"],
                output_schema="PolishReport",
                reason="用户只要求润色，这属于专业改写与评价任务，应先派生润色 Sub-agent。",
            )
        if "polish-and-plagiarism" in executable and "polish-and-plagiarism" not in ran_skills:
            return action("polish-and-plagiarism", "用户只要求润色，应优先调用润色与查重优化 Skill。")
        return finish("已完成润色调度边界检查；当前可执行 Skill 已处理完毕。")

    if vague_write and "writing_task" not in state:
        if not _has_path(state, "intermediate.requirement.raw_writing_task") and "intermediate.requirement.raw_writing_task" not in delegated_outputs:
            return delegate(
                role="requirement analysis specialist",
                task="Analyze the vague request, infer what is missing, and draft a structured writing task if possible.",
                input_keys=["user_request"],
                output_key="intermediate.requirement.raw_writing_task",
                skill_context=["writing-requirement-analysis"],
                prompt_refs=["skills/writing-requirement-analysis/prompts/extract_writing_task.md"],
                output_schema="WritingTask",
                reason="用户请求过于笼统，先派生需求分析 Sub-agent 判断缺失信息。",
            )
        return ask("请补充论文主题、论文类型、目标字数和格式要求。")

    if "writing_task" not in state:
        if not _has_path(state, "intermediate.requirement.raw_writing_task") and "intermediate.requirement.raw_writing_task" not in delegated_outputs:
            return delegate(
                role="requirement analysis specialist",
                task="Convert the user request into a structured writing task draft.",
                input_keys=["user_request"],
                output_key="intermediate.requirement.raw_writing_task",
                skill_context=["writing-requirement-analysis"],
                prompt_refs=["skills/writing-requirement-analysis/prompts/extract_writing_task.md"],
                output_schema="WritingTask",
                reason="需要先派生需求分析 Sub-agent 生成 raw writing_task intermediate。",
            )
        if "writing-requirement-analysis" in executable:
            return action("writing-requirement-analysis", "需求 Sub-agent 已生成 raw writing_task，需要运行 Skill 进行校验、增强、渲染和落盘。")
        return finish("已生成需求分析 intermediate，但 writing-requirement-analysis 尚无本地入口。")

    if wants_full and "literature_report" not in state:
        if not _has_path(state, "intermediate.literature_review.paper_claims") and "intermediate.literature_review.paper_claims" not in delegated_outputs:
            return delegate(
                role="literature analysis specialist",
                task="Extract key claims, methods, evidence strength, and limitations from collected reference papers.",
                input_keys=["writing_task", "references.raw_papers"],
                output_key="intermediate.literature_review.paper_claims",
                skill_context=["literature-review"],
                prompt_refs=["skills/literature-review/prompts/extract_claims.md"],
                output_schema="PaperClaimsExtraction",
                reason="完整论文需要文献综述，应先派生文献观点提取 Sub-agent。",
            )
        if not _has_path(state, "intermediate.literature_review.synthesis") and "intermediate.literature_review.synthesis" not in delegated_outputs:
            return delegate(
                role="literature synthesis specialist",
                task="Synthesize extracted paper claims into clusters, consensus, controversies, and research gaps.",
                input_keys=["writing_task", "intermediate.literature_review.paper_claims"],
                output_key="intermediate.literature_review.synthesis",
                skill_context=["literature-review"],
                prompt_refs=["skills/literature-review/prompts/synthesize.md"],
                output_schema="LiteratureSynthesis",
                reason="文献 claims 已就绪，需要派生综合分析 Sub-agent 生成 synthesis intermediate。",
            )
        if "literature-review" in executable:
            return action("literature-review", "文献 Sub-agent 已生成 claims 和 synthesis，需要运行 Skill 进行引用格式化、报告组装和落盘。")
        return finish("已生成文献 intermediate，但 literature-review 尚无本地入口。")

    if (wants_outline or wants_full) and "outline" not in state:
        if not _has_path(state, "intermediate.outline.raw_outline") and "intermediate.outline.raw_outline" not in delegated_outputs:
            return delegate(
                role="paper outline specialist",
                task="Produce a detailed structured paper outline based on the writing task and available literature context.",
                input_keys=["writing_task", "literature_report"],
                output_key="intermediate.outline.raw_outline",
                skill_context=["paper-outline"],
                prompt_refs=["skills/paper-outline/prompts/outline.md"],
                output_schema="PaperOutline",
                reason="用户需要大纲，这属于专业结构生成任务，应先派生大纲 Sub-agent。",
            )
        if "paper-outline" in executable:
            return action("paper-outline", "大纲 Sub-agent 已生成 intermediate，需要运行 paper-outline Skill 落盘正式 outline。")
        return finish("本地已完成可执行的前置 Skill；paper-outline 尚无本地入口，无法继续生成大纲。")

    if wants_full and "draft" not in state:
        if not _has_path(state, "intermediate.draft.raw_draft") and "intermediate.draft.raw_draft" not in delegated_outputs:
            return delegate(
                role="paper drafting specialist",
                task="Generate a structured draft intermediate from writing_task, literature_report, and outline.",
                input_keys=["writing_task", "literature_report", "outline"],
                output_key="intermediate.draft.raw_draft",
                skill_context=["paper-content-generation"],
                prompt_refs=["skills/paper-content-generation/prompts/draft.md"],
                output_schema="PaperDraft",
                reason="完整论文需要正文生成，应派生正文 Sub-agent。",
            )
        if "paper-content-generation" in executable:
            return action("paper-content-generation", "正文 Sub-agent 已生成 intermediate，需要运行正文 Skill 落盘 draft。")

    if wants_full and "formatted_draft" not in state:
        if not _has_path(state, "intermediate.formatting.raw_format_report") and "intermediate.formatting.raw_format_report" not in delegated_outputs:
            return delegate(
                role="academic formatting specialist",
                task="Analyze the draft against formatting requirements and produce structured formatting instructions.",
                input_keys=["writing_task", "draft"],
                output_key="intermediate.formatting.raw_format_report",
                skill_context=["academic-formatting"],
                prompt_refs=["skills/academic-formatting/prompts/format.md"],
                output_schema="FormatReport",
                reason="完整论文需要格式检查，应派生格式化 Sub-agent。",
            )
        if "academic-formatting" in executable:
            return action("academic-formatting", "格式化 Sub-agent 已生成 intermediate，需要运行格式化 Skill。")

    if wants_full and "polished_draft" not in state:
        if not _has_path(state, "intermediate.polishing.raw_polish_report") and "intermediate.polishing.raw_polish_report" not in delegated_outputs:
            return delegate(
                role="academic polishing specialist",
                task="Produce structured polishing and plagiarism-reduction suggestions for the formatted draft.",
                input_keys=["writing_task", "formatted_draft", "draft"],
                output_key="intermediate.polishing.raw_polish_report",
                skill_context=["polish-and-plagiarism"],
                prompt_refs=["skills/polish-and-plagiarism/prompts/polish.md"],
                output_schema="PolishReport",
                reason="完整论文最后需要润色与查重优化，应派生润色 Sub-agent。",
            )
        if "polish-and-plagiarism" in executable:
            return action("polish-and-plagiarism", "润色 Sub-agent 已生成 intermediate，需要运行润色 Skill。")

    if wants_outline and "outline" in state:
        return finish("已完成论文大纲生成，结果已写入 state.json 和 outputs 目录。")

    return finish("已完成当前请求所需的本地 ReAct Skill 调度。")


def _has_path(state: dict[str, Any], dotted_path: str) -> bool:
    current: Any = state
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


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
