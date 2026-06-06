"""Tool for updating ProgressLedger."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from project_store.ledger import ProgressLedger, StageStatus
from traces.store import TraceStore


class UpdateProgressInput(BaseModel):
    stage_id: str
    status: StageStatus
    input_artifacts: list[str] = Field(default_factory=list)
    output_artifacts: list[str] = Field(default_factory=list)
    blocked_reason: str | None = None


def update_progress(
    progress_path: str | Path,
    stage_id: str,
    status: StageStatus,
    input_artifacts: list[str] | None = None,
    output_artifacts: list[str] | None = None,
    blocked_reason: str | None = None,
    *,
    trace_store: TraceStore | None = None,
) -> dict[str, Any]:
    ledger = ProgressLedger.load(progress_path)
    stage = ledger.update_stage(
        stage_id,
        status,
        input_artifacts=input_artifacts or [],
        output_artifacts=output_artifacts or [],
        blocked_reason=blocked_reason,
    )
    ledger.save(progress_path)
    payload = {"status": "ok", "stage": stage.model_dump(), "current_stage": ledger.current_stage}
    if trace_store is not None:
        trace_store.append("progress_update", payload=payload)
    return payload
