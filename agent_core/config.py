"""Configuration helpers for local writeAgent execution."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SKILL_PACK_ID = "academic-paper-writing"

load_dotenv(REPO_ROOT / ".env", override=True)


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
    kwargs: dict[str, object] = {"model": model_name, "temperature": temperature}
    if api_key:
        kwargs["api_key"] = api_key
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


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
    def agents_config_path(self) -> Path:
        configured = os.getenv("WRITEAGENT_AGENTS_CONFIG")
        return Path(configured) if configured else self.repo_root / "config" / "agents.yaml"

    @property
    def allowed_roots(self) -> list[Path]:
        return [self.repo_root, self.workspace_root, self.project_root]

    def ensure_dirs(self) -> None:
        for path in [self.workspace_root, self.project_root, self.artifact_root, self.trace_path.parent]:
            path.mkdir(parents=True, exist_ok=True)
