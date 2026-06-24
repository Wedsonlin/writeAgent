"""Artifact business metadata schemas."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ArtifactType(str, Enum):
    writing_task = "writing_task"
    literature_report = "literature_report"
    outline = "outline"
    draft = "draft"
    formatted_draft = "formatted_draft"
    polished_draft = "polished_draft"
    citation_package = "citation_package"
    search_evidence = "search_evidence"
    other = "other"


class ArtifactRef(BaseModel):
    artifact_id: str
    artifact_type: str
    path: str
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactMeta(BaseModel):
    artifact_id: str
    artifact_type: str
    schema_name: str | None = None
    path: str
    summary: str | None = None
    stage_id: str | None = None
    created_by: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    version: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)

    def ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.artifact_id,
            artifact_type=self.artifact_type,
            path=self.path,
            summary=self.summary,
            metadata=self.metadata,
        )
