"""Project metadata."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class ProjectInfo(BaseModel):
    project_id: str
    workspace_id: str
    root: str

    @classmethod
    def from_root(cls, project_id: str, workspace_id: str, root: str | Path) -> "ProjectInfo":
        return cls(project_id=project_id, workspace_id=workspace_id, root=str(Path(root).resolve()))
