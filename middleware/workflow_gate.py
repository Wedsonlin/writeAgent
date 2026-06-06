"""Deep Agents middleware marker for workflow gate integration."""

from __future__ import annotations

from artifacts.manifest import ArtifactManifest
from workflows.gate import WorkflowGateDecision, can_execute_skill, evaluate_stage_gate
from workflows.loader import WorkflowDefinition


class WorkflowGateMiddleware:
    name = "writeagent_workflow_gate"

    def __init__(self, workflow: WorkflowDefinition, manifest: ArtifactManifest) -> None:
        self.workflow = workflow
        self.manifest = manifest

    def evaluate_stage(self, stage_id: str) -> WorkflowGateDecision:
        return evaluate_stage_gate(self.workflow, self.manifest, stage_id)

    def evaluate_skill(self, skill_name: str) -> WorkflowGateDecision:
        return can_execute_skill(self.workflow, self.manifest, skill_name)
