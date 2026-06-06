from __future__ import annotations

from artifacts.manifest import ArtifactManifest
from artifacts.schemas import ArtifactMeta
from workflows.gate import evaluate_stage_gate
from workflows.loader import load_workflow


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
