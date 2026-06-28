from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from agent_core.config import RuntimeConfig
from server import webapp


def test_project_sessions_are_saved_under_projects_and_listed(monkeypatch, tmp_path):
    base_cfg = RuntimeConfig(repo_root=Path.cwd(), workspace_root=tmp_path / ".writeagent")
    monkeypatch.setattr(webapp, "_config", lambda: base_cfg)
    client = TestClient(webapp.app)

    thread_id = "8f3a1234-1111-4222-8333-abcdefabcdef"
    project_id = f"20260627-101112_thread-{thread_id}"

    created = client.post(
        "/api/sessions",
        json={
            "project_id": project_id,
            "thread_id": thread_id,
            "created_at": "2026-06-27T02:11:12.000Z",
        },
    )

    assert created.status_code == 200
    payload = created.json()
    assert payload["project_id"] == project_id
    assert payload["thread_id"] == thread_id
    assert payload["created_at"] == "2026-06-27T02:11:12.000Z"

    session_path = base_cfg.for_project(project_id).project_root / "session.json"
    assert session_path.exists()
    saved = json.loads(session_path.read_text(encoding="utf-8"))
    assert saved["project_id"] == project_id
    assert saved["thread_id"] == thread_id
    client.put(
        f"/api/sessions/{project_id}/messages",
        json={"messages": [{"type": "human", "content": "listed session"}]},
    )

    legacy_thread_id = "9f3a1234-1111-4222-8333-abcdefabcdef"
    legacy_project_id = f"20260626-143012_thread-{legacy_thread_id}"
    legacy_cfg = base_cfg.for_project(legacy_project_id)
    legacy_cfg.ensure_dirs()
    (legacy_cfg.artifact_root / "01-论文写作任务书.json").write_text("{}", encoding="utf-8")

    listed = client.get("/api/sessions")

    assert listed.status_code == 200
    sessions = listed.json()["sessions"]
    assert [item["project_id"] for item in sessions] == [project_id, legacy_project_id]
    assert sessions[0]["root"].endswith(f".writeagent/projects/{project_id}".replace("/", "\\"))
    assert sessions[1]["thread_id"] == legacy_thread_id


def test_empty_project_sessions_are_cleaned_when_sessions_are_listed(monkeypatch, tmp_path):
    base_cfg = RuntimeConfig(repo_root=Path.cwd(), workspace_root=tmp_path / ".writeagent")
    monkeypatch.setattr(webapp, "_config", lambda: base_cfg)
    client = TestClient(webapp.app)

    empty_thread_id = "8f3a1234-1111-4222-8333-abcdefabcdef"
    empty_project_id = f"20260627-101112_thread-{empty_thread_id}"
    kept_thread_id = "9f3a1234-1111-4222-8333-abcdefabcdef"
    kept_project_id = f"20260627-101113_thread-{kept_thread_id}"

    empty = client.post(
        "/api/sessions",
        json={
            "project_id": empty_project_id,
            "thread_id": empty_thread_id,
            "created_at": "2026-06-27T02:11:12.000Z",
        },
    )
    assert empty.status_code == 200

    kept = client.post(
        "/api/sessions",
        json={
            "project_id": kept_project_id,
            "thread_id": kept_thread_id,
            "created_at": "2026-06-27T02:11:13.000Z",
        },
    )
    assert kept.status_code == 200
    client.put(
        f"/api/sessions/{kept_project_id}/messages",
        json={"messages": [{"type": "human", "content": "keep me"}]},
    )

    listed = client.get("/api/sessions")

    assert listed.status_code == 200
    project_ids = [item["project_id"] for item in listed.json()["sessions"]]
    assert empty_project_id not in project_ids
    assert kept_project_id in project_ids
    assert not base_cfg.for_project(empty_project_id).project_root.exists()
    assert base_cfg.for_project(kept_project_id).project_root.exists()


def test_project_session_messages_are_saved_under_project_root(monkeypatch, tmp_path):
    base_cfg = RuntimeConfig(repo_root=Path.cwd(), workspace_root=tmp_path / ".writeagent")
    monkeypatch.setattr(webapp, "_config", lambda: base_cfg)
    client = TestClient(webapp.app)

    thread_id = "8f3a1234-1111-4222-8333-abcdefabcdef"
    project_id = f"20260627-101112_thread-{thread_id}"
    messages = [
        {"id": "m1", "type": "human", "content": "旧会话问题"},
        {"id": "m2", "type": "ai", "content": "已记录到项目目录"},
    ]

    saved = client.put(f"/api/sessions/{project_id}/messages", json={"messages": messages})

    assert saved.status_code == 200
    assert saved.json()["project_id"] == project_id
    assert saved.json()["messages"] == messages

    messages_path = base_cfg.for_project(project_id).project_root / "session_messages.json"
    assert messages_path.exists()
    assert json.loads(messages_path.read_text(encoding="utf-8"))["messages"] == messages

    loaded = client.get(f"/api/sessions/{project_id}/messages")
    assert loaded.status_code == 200
    assert loaded.json()["messages"] == messages

    missing = client.get(f"/api/sessions/20260627-000000_thread-9f3a1234-1111-4222-8333-abcdefabcdef/messages")
    assert missing.status_code == 200
    assert missing.json()["messages"] == []


def test_project_session_messages_fall_back_to_conversation_history(monkeypatch, tmp_path):
    base_cfg = RuntimeConfig(repo_root=tmp_path, workspace_root=tmp_path / ".writeagent")
    monkeypatch.setattr(webapp, "_config", lambda: base_cfg)
    client = TestClient(webapp.app)

    thread_id = "8f3a1234-1111-4222-8333-abcdefabcdef"
    project_id = f"20260627-101112_thread-{thread_id}"
    history_root = tmp_path / "conversation_history"
    history_root.mkdir()
    (history_root / f"{thread_id}.md").write_text(
        "\n".join(
            [
                "## Summarized at 2026-06-27T03:13:31Z",
                "",
                "Human: 旧会话需求",
                "跨行补充",
                "",
                "AI: 已记录旧会话",
                "",
                "Tool: 工具返回",
            ]
        ),
        encoding="utf-8",
    )

    loaded = client.get(f"/api/sessions/{project_id}/messages")

    assert loaded.status_code == 200
    assert loaded.json()["messages"] == [
        {"type": "human", "content": "旧会话需求\n跨行补充"},
        {"type": "ai", "content": "已记录旧会话"},
        {"type": "tool", "content": "工具返回"},
    ]


def test_frontend_support_routes_allow_local_vite_origins(monkeypatch, tmp_path):
    base_cfg = RuntimeConfig(repo_root=Path.cwd(), workspace_root=tmp_path / ".writeagent")
    monkeypatch.setattr(webapp, "_config", lambda: base_cfg)
    client = TestClient(webapp.app)

    response = client.options(
        "/api/sessions",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
