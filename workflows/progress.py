"""Workflow progress helpers."""

from __future__ import annotations

from project_store.ledger import ProgressLedger
from .loader import WorkflowDefinition


def create_progress_ledger(workflow: WorkflowDefinition) -> ProgressLedger:
    return ProgressLedger.create(workflow.id, workflow.stage_ids)


def next_stage(workflow: WorkflowDefinition, ledger: ProgressLedger) -> str | None:
    for stage in workflow.stages:
        progress = ledger.stages.get(stage.id)
        if progress is None or progress.status != "completed":
            return stage.id
    return None
