from __future__ import annotations

import json
from pathlib import Path

from agent.console_view import classify_observation_issue, compact_workspace_path
from agent.react.skill_contract_inference import build_contract_inference_prompt, generated_contract_path
from agent.react.skill_contracts import load_skill_contract, render_contract_for_prompt


def test_skill_contract_loads_explicit_json(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    (skill_dir / "contract.json").write_text(
        json.dumps(
            {
                "required_state_keys": ["writing_task"],
                "required_intermediate_keys": ["intermediate.x"],
                "formal_outputs": ["outline"],
                "subagent_prerequisites": [
                    {
                        "role": "analyst",
                        "task": "produce x",
                        "input_keys": ["writing_task"],
                        "output_key": "intermediate.x",
                        "output_schema": {"type": "object", "required": ["items"]},
                    }
                ],
                "common_errors": ["intermediate.x missing"],
            }
        ),
        encoding="utf-8",
    )

    contract = load_skill_contract(skill_dir)
    rendered = "\n".join(render_contract_for_prompt(contract))

    assert contract.required_state_keys == ["writing_task"]
    assert contract.subagent_prerequisites[0].output_key == "intermediate.x"
    assert "intermediate.x" in rendered
    assert "output_schema" in rendered


def test_missing_skill_contract_returns_empty_default(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()

    contract = load_skill_contract(skill_dir)

    assert contract.is_empty
    assert render_contract_for_prompt(contract) == []


def test_literature_review_contract_declares_prerequisites() -> None:
    repo = Path(__file__).resolve().parents[1]
    contract = load_skill_contract(repo / "skills" / "literature-review")

    assert "writing_task" in contract.required_state_keys
    assert "intermediate.literature_review.paper_claims" in contract.required_intermediate_keys
    assert "intermediate.literature_review.synthesis" in contract.required_intermediate_keys
    assert [item.output_key for item in contract.subagent_prerequisites] == [
        "intermediate.literature_review.paper_claims",
        "intermediate.literature_review.synthesis",
    ]
    paper_schema = contract.subagent_prerequisites[0].output_schema
    assert isinstance(paper_schema, dict)
    assert paper_schema["required"] == ["papers"]


def test_contract_inference_prompt_is_scaffold_only(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Skill\n\nUse it carefully.", encoding="utf-8")

    prompt = build_contract_inference_prompt(skill_dir)

    assert "Infer a deterministic writeAgent SkillContract" in prompt
    assert generated_contract_path(skill_dir).name == "contract.generated.json"


def test_console_issue_classification_and_path_compaction() -> None:
    assert classify_observation_issue({"stderr_tail": "intermediate.x missing. Run a sub-agent."}) == "missing prerequisite"
    assert classify_observation_issue({"error": "Input should be a valid dictionary [type=dict_type]"}) == "schema mismatch"
    assert classify_observation_issue({"stderr_tail": "validation failed (1 validation error)"}) == "validation warning"
    assert compact_workspace_path(r"C:\repo\.writeagent\outputs\outline.md") == "outputs/outline.md"
