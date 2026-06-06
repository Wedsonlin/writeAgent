"""workflow.yaml loading."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class WorkflowStage(BaseModel):
    id: str
    title: str
    skill: str
    requires: list[str] = Field(default_factory=list)
    produces: list[str] = Field(default_factory=list)
    description: str = ""
    quality_checks: list[str] = Field(default_factory=list)


class WorkflowDefinition(BaseModel):
    id: str
    title: str
    stages: list[WorkflowStage]

    @property
    def stage_ids(self) -> list[str]:
        return [stage.id for stage in self.stages]

    def stage(self, stage_id: str) -> WorkflowStage:
        for stage in self.stages:
            if stage.id == stage_id:
                return stage
        raise KeyError(f"Unknown workflow stage: {stage_id}")

    def previous_stage_id(self, stage_id: str) -> str | None:
        ids = self.stage_ids
        if stage_id not in ids:
            return None
        idx = ids.index(stage_id)
        return ids[idx - 1] if idx > 0 else None


def load_workflow(path: str | Path) -> WorkflowDefinition:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pyyaml is required to load workflow definitions") from exc
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return WorkflowDefinition.model_validate(payload)
