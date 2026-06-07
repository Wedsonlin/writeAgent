"""Load local subagents and remote delegation agents from configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .agent_config import AgentConfig, AgentsConfig
from .registry import AgentRegistration, AgentRegistry


@dataclass
class DiscoveredAgents:
    """Agents split by their runtime path."""

    subagents: list[dict[str, Any]] = field(default_factory=list)
    registry: AgentRegistry = field(default_factory=AgentRegistry)
    capability_routing: dict[str, str] = field(default_factory=dict)
    disable_general_purpose: bool = False


class AgentDiscovery:
    """Build Deep Agents subagents and delegation registry entries."""

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        skill_pack_root: str | Path,
        repo_root: str | Path,
    ) -> DiscoveredAgents:
        config_path = Path(path)
        if not config_path.exists():
            return DiscoveredAgents()

        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        config = AgentsConfig.model_validate(payload)
        repo = Path(repo_root).resolve()

        discovered = DiscoveredAgents(disable_general_purpose=config.disable_general_purpose)
        subagent_names: set[str] = set()

        for agent in config.agents:
            cls._register_capability(discovered, agent)
            if agent.routing == "subagent":
                subagent = cls._build_subagent(agent, repo)
                name = str(subagent["name"])
                if name in subagent_names:
                    raise ValueError(f"duplicate subagent name: {name}")
                subagent_names.add(name)
                discovered.subagents.append(subagent)
            else:
                discovered.registry.register(cls._build_registration(agent))

        return discovered

    @staticmethod
    def _register_capability(discovered: DiscoveredAgents, agent: AgentConfig) -> None:
        existing = discovered.capability_routing.get(agent.capability)
        if existing is not None:
            raise ValueError(f"duplicate capability routing for {agent.capability}: {existing} and {agent.routing}")
        discovered.capability_routing[agent.capability] = agent.routing

    @classmethod
    def _build_subagent(cls, agent: AgentConfig, repo_root: Path) -> dict[str, Any]:
        if agent.subagent is None:  # Guarded by schema validation.
            raise ValueError(f"missing subagent block for {agent.id}")

        prompt_path = cls._resolve_path(agent.subagent.prompt_file, repo_root)
        skills = [str(cls._resolve_path(skill, repo_root)) for skill in agent.subagent.skills]
        subagent: dict[str, Any] = {
            "name": agent.subagent.name,
            "description": agent.subagent.description,
            "system_prompt": prompt_path.read_text(encoding="utf-8"),
        }
        if skills:
            subagent["skills"] = skills
        if agent.subagent.model is not None:
            subagent["model"] = agent.subagent.model
        return subagent

    @staticmethod
    def _build_registration(agent: AgentConfig) -> AgentRegistration:
        if agent.backend is None:  # Guarded by schema validation.
            raise ValueError(f"missing backend for {agent.id}")

        metadata = dict(agent.metadata)
        if agent.endpoint is not None:
            metadata["endpoint"] = agent.endpoint
        handle = {"endpoint": agent.endpoint} if agent.endpoint is not None else None
        return AgentRegistration(
            agent_id=agent.id,
            capabilities=[agent.capability],
            backend=agent.backend,
            handle=handle,
            metadata=metadata,
        )

    @staticmethod
    def _resolve_path(raw_path: str, repo_root: Path) -> Path:
        path = Path(raw_path)
        if not path.is_absolute():
            path = repo_root / path
        return path.resolve()
