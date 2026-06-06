"""Business workflow progress ledger."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


StageStatus = Literal["pending", "in_progress", "completed", "blocked", "failed"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StageProgress(BaseModel):
    stage_id: str
    status: StageStatus = "pending"
    input_artifacts: list[str] = Field(default_factory=list)
    output_artifacts: list[str] = Field(default_factory=list)
    blocked_reason: str | None = None
    updated_at: str = Field(default_factory=utc_now)


class ProgressLedger(BaseModel):
    workflow_id: str
    current_stage: str | None = None
    stages: dict[str, StageProgress] = Field(default_factory=dict)
    blocked_reason: str | None = None
    updated_at: str = Field(default_factory=utc_now)

    @classmethod
    def create(cls, workflow_id: str, stage_ids: list[str]) -> "ProgressLedger":
        return cls(
            workflow_id=workflow_id,
            current_stage=stage_ids[0] if stage_ids else None,
            stages={stage_id: StageProgress(stage_id=stage_id) for stage_id in stage_ids},
        )

    @classmethod
    def load(cls, path: str | Path) -> "ProgressLedger":
        p = Path(path)
        return cls.model_validate(json.loads(p.read_text(encoding="utf-8")))

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    def update_stage(
        self,
        stage_id: str,
        status: StageStatus,
        *,
        input_artifacts: list[str] | None = None,
        output_artifacts: list[str] | None = None,
        blocked_reason: str | None = None,
    ) -> StageProgress:
        stage = self.stages.setdefault(stage_id, StageProgress(stage_id=stage_id))
        stage.status = status
        if input_artifacts is not None:
            stage.input_artifacts = input_artifacts
        if output_artifacts is not None:
            stage.output_artifacts = output_artifacts
        stage.blocked_reason = blocked_reason
        stage.updated_at = utc_now()
        self.blocked_reason = blocked_reason if status == "blocked" else None
        if status in {"in_progress", "blocked", "failed"}:
            self.current_stage = stage_id
        elif status == "completed":
            self.current_stage = self.next_recommended_stage(after=stage_id)
        self.updated_at = utc_now()
        return stage

    def completed_stages(self) -> list[str]:
        return [stage_id for stage_id, stage in self.stages.items() if stage.status == "completed"]

    def pending_stages(self) -> list[str]:
        return [stage_id for stage_id, stage in self.stages.items() if stage.status == "pending"]

    def next_recommended_stage(self, *, after: str | None = None) -> str | None:
        keys = list(self.stages)
        if after and after in keys:
            keys = keys[keys.index(after) + 1:]
        for stage_id in keys:
            if self.stages[stage_id].status != "completed":
                return stage_id
        return None
