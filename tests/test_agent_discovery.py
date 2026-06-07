from __future__ import annotations

from pathlib import Path

import pytest

from delegation.discovery import AgentDiscovery


def test_agent_discovery_loads_default_local_subagents():
    repo_root = Path.cwd()

    discovered = AgentDiscovery.load(
        repo_root / "config" / "agents.yaml",
        skill_pack_root=repo_root / "skill_packs" / "academic-paper-writing",
        repo_root=repo_root,
    )

    names = {subagent["name"] for subagent in discovered.subagents}
    assert names == {
        "requirement-analysis-agent",
        "literature-review-agent",
        "paper-outline-agent",
        "content-generation-agent",
        "academic-formatting-agent",
        "polish-plagiarism-agent",
    }
    assert discovered.registry.all() == []
    assert discovered.disable_general_purpose is True
    assert discovered.capability_routing["requirement_analysis"] == "subagent"
    assert "requirement-analysis specialist" in discovered.subagents[0]["system_prompt"]
    assert all(Path(skill).is_absolute() for subagent in discovered.subagents for skill in subagent.get("skills", []))


def test_agent_discovery_registers_remote_delegation_agent(tmp_path):
    config_path = tmp_path / "agents.yaml"
    config_path.write_text(
        """
version: 1
agents:
  - id: remote-literature
    routing: delegation
    capability: literature_review
    stage_id: literature_review
    backend: remote_a2a
    endpoint: https://lobster.example/a2a/literature
    metadata:
      platform: lobster
""",
        encoding="utf-8",
    )

    discovered = AgentDiscovery.load(
        config_path,
        skill_pack_root=tmp_path / "skill_packs",
        repo_root=tmp_path,
    )

    registration = discovered.registry.get("remote-literature")
    assert discovered.subagents == []
    assert registration is not None
    assert registration.backend == "remote_a2a"
    assert registration.capabilities == ["literature_review"]
    assert registration.handle == {"endpoint": "https://lobster.example/a2a/literature"}
    assert registration.metadata["endpoint"] == "https://lobster.example/a2a/literature"
    assert registration.metadata["platform"] == "lobster"


def test_agent_discovery_rejects_duplicate_capability_routes(tmp_path):
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("You are local.", encoding="utf-8")
    config_path = tmp_path / "agents.yaml"
    config_path.write_text(
        f"""
version: 1
agents:
  - id: local-literature
    routing: subagent
    capability: literature_review
    subagent:
      name: local-literature-agent
      description: Local literature work.
      prompt_file: {prompt_path}
  - id: remote-literature
    routing: delegation
    capability: literature_review
    backend: remote_a2a
    endpoint: https://lobster.example/a2a/literature
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate capability routing"):
        AgentDiscovery.load(config_path, skill_pack_root=tmp_path / "skill_packs", repo_root=tmp_path)
