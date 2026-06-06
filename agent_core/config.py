"""Configuration helpers for local writeAgent execution."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SKILL_PACK_ID = "academic-paper-writing"


@dataclass
class ModelConfig:
    model: str | object | None = None
    temperature: float = 0.2

    @classmethod
    def from_env(cls) -> "ModelConfig":
        return cls(model=os.getenv("WRITEAGENT_MODEL") or os.getenv("MODEL") or "openai:gpt-5.4-mini")


@dataclass
class RuntimeConfig:
    repo_root: Path = REPO_ROOT
    workspace_root: Path = REPO_ROOT / ".writeagent"
    project_root: Path = REPO_ROOT / ".writeagent" / "projects" / "default"
    skill_pack_id: str = DEFAULT_SKILL_PACK_ID
    model: ModelConfig = field(default_factory=ModelConfig.from_env)
    bash_timeout_sec: int = 60

    @property
    def skill_pack_root(self) -> Path:
        return self.repo_root / "skill_packs" / self.skill_pack_id

    @property
    def artifact_root(self) -> Path:
        return self.project_root / "artifacts"

    @property
    def progress_path(self) -> Path:
        return self.project_root / "progress.json"

    @property
    def manifest_path(self) -> Path:
        return self.artifact_root / "manifest.json"

    @property
    def trace_path(self) -> Path:
        return self.project_root / "traces" / "trace.jsonl"

    @property
    def allowed_roots(self) -> list[Path]:
        return [self.repo_root, self.workspace_root, self.project_root]

    def ensure_dirs(self) -> None:
        for path in [self.workspace_root, self.project_root, self.artifact_root, self.trace_path.parent]:
            path.mkdir(parents=True, exist_ok=True)
