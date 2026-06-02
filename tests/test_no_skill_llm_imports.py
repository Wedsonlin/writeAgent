from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_skill_entry_scripts_do_not_call_llm() -> None:
    forbidden_imports = {"_shared.llm", "agent.llm_gateway", "agent.llm_client"}
    forbidden_calls = {"chat", "structured_json", "repair_json"}
    violations: list[str] = []

    for path in (REPO_ROOT / "skills").glob("*/scripts/run.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in forbidden_imports:
                violations.append(f"{path}: imports {node.module}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in forbidden_imports:
                        violations.append(f"{path}: imports {alias.name}")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in forbidden_calls:
                violations.append(f"{path}: calls {node.func.id}()")

    assert violations == []


def test_skill_instructions_do_not_describe_skill_side_llm_calls() -> None:
    checked_paths = [
        REPO_ROOT / "skills" / "writing-requirement-analysis" / "SKILL.md",
        REPO_ROOT / "skills" / "literature-review" / "SKILL.md",
        REPO_ROOT / "docs" / "02-OpenClaw适配方案.md",
    ]
    forbidden_phrases = [
        "_shared.llm",
        "WRITEAGENT_LLM_API_KEY",
        "调用 LLM 用",
        "所有 Skill 通过",
        "Skill script 通过",
        "Skill 自动重试",
        "Mock 模式",
        "mock LLM",
    ]
    violations: list[str] = []

    for path in checked_paths:
        text = path.read_text(encoding="utf-8")
        for phrase in forbidden_phrases:
            if phrase in text:
                violations.append(f"{path}: contains stale phrase {phrase!r}")

    assert violations == []


def test_skill_metadata_disables_direct_model_invocation() -> None:
    for path in (REPO_ROOT / "skills").glob("*/SKILL.md"):
        text = path.read_text(encoding="utf-8")
        assert "disable-model-invocation: true" in text
        assert '"env"' not in text
        assert "primaryEnv" not in text
