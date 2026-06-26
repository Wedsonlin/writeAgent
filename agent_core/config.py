"""Configuration helpers for local writeAgent execution."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SKILL_PACK_ID = "academic-paper-writing"

load_dotenv(REPO_ROOT / ".env", override=True)


STAGE_ARTIFACT_BASENAMES = {
    "requirement_analysis": "01-论文写作任务书",
    "literature_review": "02-文献处理报告",
    "paper_outline": "03-论文详细大纲",
    "content_generation": "04-分章节初稿",
    "academic_formatting": "05-格式规范的论文终稿",
    "polish_and_plagiarism": "06-润色论文终稿",
}


def _default_workspace_root() -> Path:
    configured = os.getenv("WRITEAGENT_WORKSPACE")
    return Path(configured) if configured else REPO_ROOT / ".writeagent"


def sanitize_project_id(project_id: str | None) -> str:
    raw = str(project_id or "").strip()
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", raw.replace("\\", "/").replace("/", "-"))
    cleaned = cleaned.strip("._-")
    if not cleaned or cleaned in {".", ".."}:
        return "default"
    return cleaned[:120]


@dataclass
class ModelConfig:
    model: str | object | None = None
    temperature: float = 0.2

    @classmethod
    def from_env(cls) -> "ModelConfig":
        temperature = float(os.getenv("WRITEAGENT_TEMPERATURE", "0.2"))
        model = os.getenv("WRITEAGENT_MODEL") or os.getenv("MODEL") or "openai:gpt-5.4-mini"
        api_key = os.getenv("WRITEAGENT_LLM_API_KEY")
        base_url = os.getenv("WRITEAGENT_LLM_BASE_URL")
        if api_key or base_url:
            return cls(model=_openai_compatible_model(model, api_key=api_key, base_url=base_url, temperature=temperature))
        return cls(model=model, temperature=temperature)


def _openai_compatible_model(model: str, *, api_key: str | None, base_url: str | None, temperature: float) -> object:
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("langchain-openai is required for WRITEAGENT_LLM_* configuration.") from exc

    model_name = model.removeprefix("openai:")
    disable_streaming = os.getenv("WRITEAGENT_DISABLE_MODEL_STREAMING", "1").lower() not in {"0", "false", "no"}
    kwargs: dict[str, object] = {
        "model": model_name,
        "temperature": temperature,
        "disable_streaming": disable_streaming,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


@dataclass
class RuntimeConfig:
    repo_root: Path = REPO_ROOT
    workspace_root: Path = field(default_factory=_default_workspace_root)
    project_id: str = "default"
    project_root: Path | None = None
    skill_pack_id: str = DEFAULT_SKILL_PACK_ID
    model: ModelConfig = field(default_factory=ModelConfig.from_env)
    bash_timeout_sec: int = 60

    def __post_init__(self) -> None:
        self.repo_root = Path(self.repo_root)
        self.workspace_root = Path(self.workspace_root)
        self.project_id = sanitize_project_id(self.project_id)
        if self.project_root is None:
            self.project_root = self.workspace_root / "projects" / self.project_id
        else:
            self.project_root = Path(self.project_root)
            if self.project_id == "default" and self.project_root.name:
                self.project_id = sanitize_project_id(self.project_root.name)

    def for_project(self, project_id: str | None) -> "RuntimeConfig":
        return RuntimeConfig(
            repo_root=self.repo_root,
            workspace_root=self.workspace_root,
            project_id=sanitize_project_id(project_id),
            skill_pack_id=self.skill_pack_id,
            model=self.model,
            bash_timeout_sec=self.bash_timeout_sec,
        )

    @property
    def skill_pack_root(self) -> Path:
        return self.repo_root / "skill_packs" / self.skill_pack_id

    @property
    def artifact_root(self) -> Path:
        return self.project_root / "artifacts"

    @property
    def tmp_root(self) -> Path:
        return self.project_root / "tmp"

    @property
    def evidence_root(self) -> Path:
        return self.project_root / "evidence"

    @property
    def cache_root(self) -> Path:
        return self.project_root / "cache"

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
    def agents_config_path(self) -> Path:
        configured = os.getenv("WRITEAGENT_AGENTS_CONFIG")
        return Path(configured) if configured else self.repo_root / "config" / "agents.yaml"

    @property
    def allowed_roots(self) -> list[Path]:
        return [self.repo_root, self.workspace_root, self.project_root]

    def ensure_dirs(self) -> None:
        for path in [
            self.workspace_root,
            self.project_root,
            self.artifact_root,
            self.tmp_root,
            self.evidence_root,
            self.cache_root,
            self.trace_path.parent,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def stage_artifact_path(self, stage_id: str, suffix: str = ".json") -> Path:
        basename = STAGE_ARTIFACT_BASENAMES[stage_id]
        normalized_suffix = suffix if suffix.startswith(".") else f".{suffix}"
        return self.artifact_root / f"{basename}{normalized_suffix}"
