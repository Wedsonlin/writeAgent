from __future__ import annotations

from pathlib import Path


def test_system_prompt_keeps_project_artifact_layout_contract():
    text = Path("skill_packs/academic-paper-writing/system_prompt.md").read_text(encoding="utf-8")

    assert "projects/default/artifacts" not in text
    assert "current project's `artifacts/` directory" in text
    assert "01-论文写作任务书.md" in text
    assert "04-分章节初稿.md" in text
    assert "06-润色论文终稿.pdf" in text
    assert "temporary Skill input JSON" in text
    assert "search evidence" in text


def test_agent_prompts_keep_recovery_contracts_for_content_and_polish():
    content = Path("config/agent_prompts/content-generation.md").read_text(encoding="utf-8")
    polish = Path("config/agent_prompts/polish-plagiarism.md").read_text(encoding="utf-8")

    assert "Do not run `paper-content-generation/scripts/run.py` when `draft` is absent" in content
    assert "Do not ask the user to provide an external draft" in content
    assert "citation reconciliation gate" in content
    assert "treat `content_markdown.citation_marker` as a recoverable input error" in content

    assert "Do not run the deterministic script when `polished_markdown` is absent" in polish
    assert "Do not ask the user to provide an external polished draft" in polish
    assert "heading and citation preservation gate" in polish
    assert "treat it as a recoverable polished-input preservation error" in polish


def test_frontend_static_contracts_for_tool_cards_and_thread_ids():
    tool_view = Path("frontend/src/components/ToolDisplayView.tsx").read_text(encoding="utf-8")
    app = Path("frontend/src/App.tsx").read_text(encoding="utf-8")
    project_session = Path("frontend/src/lib/projectSession.ts").read_text(encoding="utf-8")

    assert "tool-path-list" not in tool_view
    assert "display.paths.map" not in tool_view
    assert "normalizeThreadId" in project_session
    assert "extract UUID" not in project_session
    assert "normalizeThreadId(projectSession.threadId)" in app
    assert "project_id" in app
