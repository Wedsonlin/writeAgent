from __future__ import annotations

import json

from artifacts.manifest import ArtifactManifest
from artifacts.schemas import ArtifactMeta
from middleware.workflow_gate import WorkflowGateMiddleware
from workflows.gate import evaluate_stage_gate
from workflows.loader import load_workflow


class FakeToolRequest:
    name = "execute_bash"

    def __init__(self, command: str) -> None:
        self.args = {"command": command}
        self.tool_call_id = "call-1"


def test_workflow_gate_blocks_missing_artifacts(tmp_path):
    workflow = load_workflow("skill_packs/academic-paper-writing/workflow.yaml")
    manifest = ArtifactManifest.load(tmp_path / "manifest.json")
    decision = evaluate_stage_gate(workflow, manifest, "literature_review")
    assert decision.status == "blocked"
    assert decision.missing_artifacts == ["writing_task"]
    assert decision.next_recommended_stage == "requirement_analysis"


def test_workflow_gate_allows_when_requires_met(tmp_path):
    workflow = load_workflow("skill_packs/academic-paper-writing/workflow.yaml")
    manifest = ArtifactManifest.load(tmp_path / "manifest.json")
    manifest.upsert(ArtifactMeta(artifact_id="task", artifact_type="writing_task", path="task.json"))
    decision = evaluate_stage_gate(workflow, manifest, "literature_review")
    assert decision.status == "allowed"


def test_workflow_gate_middleware_blocks_skill_when_required_artifacts_are_missing(tmp_path):
    workflow = load_workflow("skill_packs/academic-paper-writing/workflow.yaml")
    manifest_path = tmp_path / "manifest.json"
    gate = WorkflowGateMiddleware(workflow, manifest_path)
    called = False

    def handler(request):
        nonlocal called
        called = True
        return {"status": "ok"}

    result = gate.wrap_tool_call(
        FakeToolRequest("python skill_packs/academic-paper-writing/skills/literature-review/scripts/run.py"),
        handler,
    )

    payload = json.loads(result.content)
    assert called is False
    assert payload["status"] == "blocked"
    assert payload["skill_name"] == "literature-review"
    assert payload["missing_artifacts"] == ["writing_task"]
    assert payload["next_recommended_stage"] == "requirement_analysis"


def test_workflow_gate_middleware_allows_skill_when_required_artifacts_exist(tmp_path):
    workflow = load_workflow("skill_packs/academic-paper-writing/workflow.yaml")
    manifest_path = tmp_path / "manifest.json"
    manifest = ArtifactManifest.load(manifest_path)
    manifest.upsert(ArtifactMeta(artifact_id="task", artifact_type="writing_task", path="task.json"))
    gate = WorkflowGateMiddleware(workflow, manifest_path)
    called = False

    def handler(request):
        nonlocal called
        called = True
        return {"status": "ok"}

    result = gate.wrap_tool_call(
        FakeToolRequest("python skill_packs/academic-paper-writing/skills/literature-review/scripts/run.py"),
        handler,
    )

    assert called is True
    assert result == {"status": "ok"}


def test_workflow_gate_middleware_passes_through_non_skill_bash_command(tmp_path):
    workflow = load_workflow("skill_packs/academic-paper-writing/workflow.yaml")
    gate = WorkflowGateMiddleware(workflow, tmp_path / "manifest.json")
    called = False

    def handler(request):
        nonlocal called
        called = True
        return {"status": "ok"}

    result = gate.wrap_tool_call(FakeToolRequest('python -c "print(123)"'), handler)

    assert called is True
    assert result == {"status": "ok"}
