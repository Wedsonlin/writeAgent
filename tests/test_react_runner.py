from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage

from agent.llm_gateway import LLMGateway
from agent.react.skill_registry import SkillRegistry
from agent.react_runner import ReactRunner
from agent.skill_runner import SkillResult


def test_react_runner_calls_inspect_state_through_bound_tool(tmp_path: Path) -> None:
    model = SequenceChatModel(
        [
            AIMessage(content="", tool_calls=[{"name": "inspect_state", "args": {}, "id": "call_inspect"}]),
            AIMessage(content="checked"),
        ]
    )
    result = _run(tmp_path, _registry_with_skills(tmp_path, []), "先检查状态。", model=model)

    assert result.status == "finished"
    assert result.answer == "checked"
    assert model.bound_tool_names == [
        "inspect_state",
        "run_skill",
        "read_workspace_file",
        "delegate_to_subagent",
        "ask_user",
    ]
    assert [step["action"] for step in result.steps] == ["inspect_state"]


def test_react_runner_calls_run_skill_tool(tmp_path: Path) -> None:
    registry = _registry_with_skills(tmp_path, ["writing-requirement-analysis"])
    result = _run(
        tmp_path,
        registry,
        "分析写作需求。",
        model=SequenceChatModel(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "run_skill",
                            "args": {"skill_name": "writing-requirement-analysis", "reason": "extract requirements"},
                            "id": "call_skill",
                        }
                    ],
                ),
                AIMessage(content="requirements done"),
            ]
        ),
    )

    state = json.loads(result.state_path.read_text(encoding="utf-8"))
    assert result.status == "finished"
    assert state["writing_task"]["produced_by"] == "writing-requirement-analysis"
    assert result.steps[0]["observation"]["status"] == "ok"


def test_react_runner_delegates_to_subagent_graph(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        _registry_with_skills(tmp_path, []),
        "请先派生需求分析子代理。",
        model=SequenceChatModel(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "delegate_to_subagent",
                            "args": {
                                "role": "requirement analyst",
                                "task": "Extract a writing task.",
                                "input_keys": ["user_request"],
                                "output_key": "intermediate.requirement.raw_writing_task",
                                "output_schema": {"type": "object"},
                            },
                            "id": "call_delegate",
                        }
                    ],
                ),
                AIMessage(content="delegated"),
            ]
        ),
    )

    state = json.loads(result.state_path.read_text(encoding="utf-8"))
    assert result.status == "finished"
    assert result.steps[0]["action"] == "delegate_to_subagent"
    assert result.steps[0]["observation"]["status"] == "completed"
    assert state["intermediate"]["requirement"]["raw_writing_task"]


def test_react_runner_ask_user_tool_ends_run(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        _registry_with_skills(tmp_path, []),
        "信息不足。",
        model=SequenceChatModel(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "ask_user",
                            "args": {"question": "请补充论文主题。", "reason": "missing topic"},
                            "id": "call_ask",
                        }
                    ],
                )
            ]
        ),
    )

    assert result.status == "ask_user"
    assert "论文主题" in result.answer


def test_react_runner_continues_after_human_answer(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        _registry_with_skills(tmp_path, []),
        "信息不足。",
        model=SequenceChatModel(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "ask_user",
                            "args": {"question": "请补充论文主题。", "reason": "missing topic"},
                            "id": "call_ask",
                        }
                    ],
                ),
                AIMessage(content="已根据补充信息继续生成。"),
            ]
        ),
        human_input_provider=lambda question, reason: "主题是生成式 AI 辅助论文写作",
    )

    assert result.status == "finished"
    assert result.answer == "已根据补充信息继续生成。"
    assert result.steps[0]["action"] == "ask_user"
    assert result.steps[0]["observation"]["status"] == "answered"
    assert "生成式 AI" in result.steps[0]["observation"]["answer"]


def test_react_runner_final_answer_does_not_require_finish_action(tmp_path: Path) -> None:
    model = SequenceChatModel([AIMessage(content="final answer")])
    result = _run(tmp_path, _registry_with_skills(tmp_path, []), "直接回答。", model=model)

    assert result.status == "finished"
    assert result.answer == "final answer"
    assert result.steps == []
    assert "finish" not in model.bound_tool_names
    assert not (Path(__file__).resolve().parents[1] / "agent" / "react" / "actions.py").exists()


class SequenceChatModel:
    def __init__(self, responses: list[AIMessage]) -> None:
        self.responses = responses
        self.bound_tool_names: list[str] = []

    def bind_tools(self, tools: list[Any]) -> "SequenceChatModel":
        self.bound_tool_names = [str(getattr(tool, "name", "")) for tool in tools]
        return self

    def invoke(self, messages: list[Any], config: dict[str, Any] | None = None) -> AIMessage:
        return self.responses.pop(0)


class FakeSkillRunner:
    def run(self, skill_name: str, state_path: Path) -> SkillResult:
        state_path = Path(state_path)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["writing_task"] = {"produced_by": skill_name}
        state["stage"] = f"{skill_name}_done"
        state_path.write_text(json.dumps(state), encoding="utf-8")
        return SkillResult(
            skill=skill_name,
            status="ok",
            duration_ms=5,
            stdout=f"{skill_name} ok",
            stderr="",
            state_after=state,
        )


def _run(
    tmp_path: Path,
    registry: SkillRegistry,
    request: str,
    *,
    model: Any,
    human_input_provider: Any | None = None,
):
    workspace = tmp_path / "workspace"
    return ReactRunner(
        llm_gateway=LLMGateway(),
        skill_registry=registry,
        skill_runner=FakeSkillRunner(),
        max_steps=8,
        model=model,
        human_input_provider=human_input_provider,
    ).run(
        user_request=request,
        workspace_root=workspace,
        state_path=workspace / "state.json",
    )


def _registry_with_skills(tmp_path: Path, skills: Any) -> SkillRegistry:
    skills_dir = tmp_path / "skills"
    for skill in skills:
        skill_dir = skills_dir / skill
        scripts = skill_dir / "scripts"
        scripts.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {skill}\ndescription: {skill} description\n---\n",
            encoding="utf-8",
        )
        (scripts / "run.py").write_text("print('ok')\n", encoding="utf-8")
    return SkillRegistry.from_skills_dir(skills_dir)
