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
