from __future__ import annotations

import json
from pathlib import Path

from agent.react.skill_registry import SkillRegistry
from agent.react.tools import create_main_tools, inspect_state, read_workspace_file, run_skill
from agent.skill_runner import SkillResult


def test_skill_registry_parses_frontmatter_and_entrypoints(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    _write_skill(skills_dir, "skill-a", "Skill A routes requests.", entrypoint=True)
    _write_skill(skills_dir, "skill-b", "Skill B is documented only.", entrypoint=False)
    (skills_dir / "_shared").mkdir(parents=True)

    registry = SkillRegistry.from_skills_dir(skills_dir)

    assert [spec.name for spec in registry.list_specs()] == ["skill-a", "skill-b"]
    assert [spec.name for spec in registry.list_executable_specs()] == ["skill-a"]
    assert registry.get("skill-a").description == "Skill A routes requests."
    rendered = registry.render_for_prompt()
    assert "executable: true" in rendered
    assert "executable: false" in rendered


def test_skill_registry_renders_contract_prerequisites(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    _write_skill(skills_dir, "skill-a", "Skill A routes requests.", entrypoint=True)
    (skills_dir / "skill-a" / "contract.json").write_text(
        json.dumps(
            {
                "required_state_keys": ["writing_task"],
                "required_intermediate_keys": ["intermediate.x"],
                "subagent_prerequisites": [
                    {
                        "role": "analyst",
                        "task": "produce x",
                        "input_keys": ["writing_task"],
                        "output_key": "intermediate.x",
                        "output_schema": {"type": "object", "required": ["items"]},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    rendered = SkillRegistry.from_skills_dir(skills_dir).render_for_prompt()

    assert "required_state_keys" in rendered
    assert "intermediate.x" in rendered
    assert "subagent_prerequisite" in rendered


def test_legacy_json_action_parser_is_not_part_of_react_entrypoint() -> None:
    assert not (Path(__file__).resolve().parents[1] / "agent" / "react" / "actions.py").exists()


def test_run_skill_returns_state_diff_and_tails(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    _write_skill(skills_dir, "writing-requirement-analysis", "Analyze requirements.", entrypoint=True)
    registry = SkillRegistry.from_skills_dir(skills_dir)
    state_path = tmp_path / "workspace" / "state.json"
    state_path.parent.mkdir()
    state_path.write_text(json.dumps({"user_request": "x", "stage": "init"}), encoding="utf-8")

    observation = run_skill(
        "writing-requirement-analysis",
        "needed",
        state_path,
        skill_registry=registry,
        skill_runner=FakeRunner({"writing-requirement-analysis": "writing_task"}),
        tail_chars=12,
    )

    assert observation["status"] == "ok"
    assert observation["produced_keys"] == ["writing_task"]
    assert observation["updated_keys"] == ["stage"]
    assert observation["stdout_tail"].endswith("stdout-tail")
    assert "writing_task" in observation["state_keys"]


def test_inspect_state_summarizes_long_values(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps({"draft": "x" * 900, "history": [{"skill": "a"}]}),
        encoding="utf-8",
    )

    observation = inspect_state(state_path)

    assert observation["status"] == "ok"
    assert observation["summary"]["draft"]["type"] == "str"
    assert observation["summary"]["draft"]["length"] == 900


def test_main_agent_registers_and_reads_workspace_file(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    _write_skill(skills_dir, "skill-a", "Skill A.", entrypoint=True)
    registry = SkillRegistry.from_skills_dir(skills_dir)
    workspace = tmp_path / "workspace"
    outputs = workspace / "outputs"
    outputs.mkdir(parents=True)
    state_path = workspace / "state.json"
    state_path.write_text("{}", encoding="utf-8")
    (outputs / "outline.md").write_text("hello outline", encoding="utf-8")

    tools = create_main_tools(
        skill_registry=registry,
        skill_runner=FakeRunner({}),
        state_path=state_path,
        subagent_runtime=None,
    )
    observation = read_workspace_file("outputs/outline.md", state_path)

    assert "read_workspace_file" in {tool.name for tool in tools}
    assert observation["status"] == "ok"
    assert observation["content"] == "hello outline"


def test_ask_user_with_human_provider_returns_answered_observation(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    _write_skill(skills_dir, "skill-a", "Skill A.", entrypoint=True)
    registry = SkillRegistry.from_skills_dir(skills_dir)
    state_path = tmp_path / "workspace" / "state.json"
    state_path.parent.mkdir()
    state_path.write_text("{}", encoding="utf-8")
    tools = {
        tool.name: tool
        for tool in create_main_tools(
            skill_registry=registry,
            skill_runner=FakeRunner({}),
            state_path=state_path,
            subagent_runtime=None,
            human_input_provider=lambda question, reason: "按默认方案继续",
        )
    }

    observation = json.loads(
        tools["ask_user"].invoke({"question": "是否继续？", "reason": "missing preferences"})
    )

    assert observation["status"] == "answered"
    assert observation["answer"] == "按默认方案继续"
    assert observation["question"] == "是否继续？"


class FakeRunner:
    def __init__(self, outputs: dict[str, str]) -> None:
        self.outputs = outputs

    def run(self, skill_name: str, state_path: Path) -> SkillResult:
        state = json.loads(Path(state_path).read_text(encoding="utf-8"))
        state[self.outputs[skill_name]] = {"produced_by": skill_name}
        state["stage"] = f"{skill_name}_done"
        Path(state_path).write_text(json.dumps(state), encoding="utf-8")
        return SkillResult(
            skill=skill_name,
            status="ok",
            duration_ms=10,
            stdout="hello stdout-tail",
            stderr="",
            state_after=state,
        )


def _write_skill(
    skills_dir: Path,
    name: str,
    description: str,
    *,
    entrypoint: bool,
) -> None:
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n",
        encoding="utf-8",
    )
    if entrypoint:
        scripts = skill_dir / "scripts"
        scripts.mkdir()
        (scripts / "run.py").write_text("print('ok')\n", encoding="utf-8")
