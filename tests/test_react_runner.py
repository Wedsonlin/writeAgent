from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent.react.skill_registry import SkillRegistry
from agent.react_runner import ReactRunner
from agent.skill_runner import SkillResult


OUTPUT_BY_SKILL = {
    "writing-requirement-analysis": "writing_task",
    "literature-review": "literature_report",
    "paper-outline": "outline",
    "paper-content-generation": "draft",
    "academic-formatting": "formatted_draft",
    "polish-and-plagiarism": "polished_draft",
}


def test_react_runner_full_writing_uses_multiple_skills(tmp_path: Path) -> None:
    registry = _registry_with_skills(tmp_path, OUTPUT_BY_SKILL.keys())
    result = _run(
        tmp_path,
        registry,
        "请根据以下研究方向生成一篇完整论文初稿：XXX，要求包含文献综述、大纲、正文、格式化和润色。",
    )

    called = _called_skills(result.steps)
    assert result.status == "finished"
    assert called == list(OUTPUT_BY_SKILL.keys())
    state = json.loads(result.state_path.read_text(encoding="utf-8"))
    assert "polished_draft" in state
    assert result.trace_path.exists()


def test_react_runner_outline_request_skips_format_and_polish(tmp_path: Path) -> None:
    registry = _registry_with_skills(tmp_path, OUTPUT_BY_SKILL.keys())
    result = _run(tmp_path, registry, "我只需要一份关于XXX的论文详细大纲。")

    called = _called_skills(result.steps)
    assert result.status == "finished"
    assert called == [
        "writing-requirement-analysis",
        "literature-review",
        "paper-outline",
    ]
    assert "academic-formatting" not in called
    assert "polish-and-plagiarism" not in called


def test_react_runner_polish_without_draft_asks_user(tmp_path: Path) -> None:
    registry = _registry_with_skills(tmp_path, OUTPUT_BY_SKILL.keys())
    result = _run(tmp_path, registry, "我已经有论文初稿，只需要语言润色和查重优化建议。")

    assert result.status == "ask_user"
    assert "初稿" in result.answer
    assert _called_skills(result.steps) == []


def test_react_runner_vague_request_asks_user(tmp_path: Path) -> None:
    registry = _registry_with_skills(tmp_path, OUTPUT_BY_SKILL.keys())
    result = _run(tmp_path, registry, "帮我写一篇论文。")

    assert result.status == "ask_user"
    assert _called_skills(result.steps) == []


def test_react_runner_skill_failure_surfaces_observation(tmp_path: Path) -> None:
    registry = _registry_with_skills(tmp_path, ["writing-requirement-analysis"])
    result = _run(
        tmp_path,
        registry,
        "请写一篇关于XXX的论文。",
        skill_runner=FakeSkillRunner(fail_on={"writing-requirement-analysis"}),
    )

    assert result.status == "ask_user"
    assert result.steps[0]["observation"]["status"] == "error"
    assert "simulated failure" in result.steps[0]["observation"]["stderr_tail"]


def test_react_runner_repairs_invalid_json_once(tmp_path: Path) -> None:
    registry = _registry_with_skills(tmp_path, [])
    result = _run(
        tmp_path,
        registry,
        "只检查状态。",
        llm=SequenceLLM(
            [
                "not json",
                '{"thought":"repaired","action":"finish","action_input":{"answer":"ok"}}',
            ]
        ),
    )

    assert result.status == "finished"
    assert result.answer == "ok"


def test_react_graph_routes_inspect_back_to_decide(tmp_path: Path) -> None:
    registry = _registry_with_skills(tmp_path, [])
    result = _run(
        tmp_path,
        registry,
        "先检查状态，然后结束。",
        llm=SequenceLLM(
            [
                '{"thought":"look","action":"inspect_state","action_input":{}}',
                '{"thought":"done","action":"finish","action_input":{"answer":"checked"}}',
            ]
        ),
    )

    assert result.status == "finished"
    assert [step["action"] for step in result.steps] == ["inspect_state", "finish"]
    trace = json.loads(result.trace_path.read_text(encoding="utf-8"))
    assert trace["status"] == "finished"


def test_react_runner_stops_at_max_steps(tmp_path: Path) -> None:
    registry = _registry_with_skills(tmp_path, [])
    result = _run(
        tmp_path,
        registry,
        "只检查状态。",
        llm=SequenceLLM(
            [
                '{"thought":"look","action":"inspect_state","action_input":{}}',
                '{"thought":"look again","action":"inspect_state","action_input":{}}',
            ]
        ),
        max_steps=2,
    )

    assert result.status == "max_steps_exceeded"
    assert len(result.steps) == 2


class EchoMockLLM:
    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        return str(kwargs["mock_response"])


class SequenceLLM:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        return self.responses.pop(0)


class FakeSkillRunner:
    def __init__(self, fail_on: set[str] | None = None) -> None:
        self.fail_on = fail_on or set()

    def run(self, skill_name: str, state_path: Path) -> SkillResult:
        state_path = Path(state_path)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if skill_name in self.fail_on:
            return SkillResult(
                skill=skill_name,
                status="error",
                duration_ms=5,
                stdout="",
                stderr="simulated failure",
                state_after={},
            )
        output_key = OUTPUT_BY_SKILL[skill_name]
        state[output_key] = {"produced_by": skill_name}
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
    llm: Any | None = None,
    skill_runner: Any | None = None,
    max_steps: int = 12,
):
    workspace = tmp_path / "workspace"
    return ReactRunner(
        llm_client=llm or EchoMockLLM(),
        skill_registry=registry,
        skill_runner=skill_runner or FakeSkillRunner(),
        max_steps=max_steps,
    ).run(
        user_request=request,
        workspace_root=workspace,
        state_path=workspace / "state.json",
    )


def _called_skills(steps: list[dict[str, Any]]) -> list[str]:
    return [
        step.get("action_input", {}).get("skill_name")
        for step in steps
        if step.get("action") == "run_skill"
    ]


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
