from __future__ import annotations

from pathlib import Path


def test_frontend_case_button_fetches_original_requirement():
    repo_root = Path.cwd()
    app_source = (repo_root / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
    api_source = (repo_root / "frontend" / "src" / "api" / "workflow.ts").read_text(encoding="utf-8")

    assert "fetchCaseRequirement" in api_source
    assert "/api/case/original-requirement" in api_source
    assert "fetchCaseRequirement" in app_source
    assert "caseWorkflowPrompt" not in app_source
    assert "setInput(caseWorkflowPrompt)" not in app_source
    assert "完整执行论文写作六阶段" not in app_source
