"""Workflow gate decisions."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from artifacts.manifest import ArtifactManifest
from .loader import WorkflowDefinition


class WorkflowGateDecision(BaseModel):
    status: Literal["allowed", "blocked"]
    reason: str = ""
    missing_artifacts: list[str] = Field(default_factory=list)
    next_recommended_stage: str | None = None
    requires_human_response: bool = False


def evaluate_stage_gate(workflow: WorkflowDefinition, manifest: ArtifactManifest, stage_id: str) -> WorkflowGateDecision:
    stage = workflow.stage(stage_id)
    missing = [artifact_type for artifact_type in stage.requires if not manifest.has_type(artifact_type)]
    if missing:
        previous = workflow.previous_stage_id(stage_id)
        return WorkflowGateDecision(
            status="blocked",
            reason=f"Stage '{stage_id}' requires upstream artifacts that are not available.",
            missing_artifacts=missing,
            next_recommended_stage=previous or workflow.stage_ids[0],
            requires_human_response=False,
        )
    return WorkflowGateDecision(status="allowed", next_recommended_stage=stage_id)


def can_execute_skill(workflow: WorkflowDefinition, manifest: ArtifactManifest, skill_name: str) -> WorkflowGateDecision:
    for stage in workflow.stages:
        if stage.skill == skill_name:
            return evaluate_stage_gate(workflow, manifest, stage.id)
    return WorkflowGateDecision(
        status="blocked",
        reason=f"Skill is not declared in workflow: {skill_name}",
        next_recommended_stage=workflow.stage_ids[0] if workflow.stage_ids else None,
    )
