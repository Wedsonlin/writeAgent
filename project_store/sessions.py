"""Project session metadata persisted under ``.writeagent/projects``."""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from agent_core.config import RuntimeConfig, sanitize_project_id


SESSION_FILENAME = "session.json"
SESSION_MESSAGES_FILENAME = "session_messages.json"
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
_PROJECT_THREAD_RE = re.compile(
    r"(?:^|_)thread-([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$",
    re.IGNORECASE,
)
_PROJECT_TIMESTAMP_RE = re.compile(r"^(\d{8})-(\d{6})(?:_|$)")
_HISTORY_LINE_RE = re.compile(r"^(Human|User|AI|Assistant|Tool|System):\s?(.*)$")
_HISTORY_ROLE_MAP = {
    "Human": "human",
    "User": "human",
    "AI": "ai",
    "Assistant": "ai",
    "Tool": "tool",
    "System": "system",
}
_HOUSEKEEPING_FILENAMES = {SESSION_FILENAME, "progress.json"}


class ProjectSessionUpsert(BaseModel):
    project_id: str | None = None
    project_name: str | None = None
    thread_id: str
    created_at: str | None = None
    updated_at: str | None = None


class ProjectSessionRecord(BaseModel):
    project_id: str
    thread_id: str
    created_at: str
    updated_at: str
    root: str


class ProjectSessionMessagesUpsert(BaseModel):
    messages: list[Any]
    updated_at: str | None = None


class ProjectSessionMessagesRecord(BaseModel):
    project_id: str
    messages: list[Any]
    updated_at: str


def upsert_project_session(cfg: RuntimeConfig, payload: ProjectSessionUpsert) -> ProjectSessionRecord:
    project_id = sanitize_project_id(payload.project_id or payload.project_name or "")
    thread_id = normalize_thread_id(payload.thread_id) or normalize_thread_id(project_id)
    if not thread_id:
        raise ValueError("thread_id must be a UUID or a project name containing one")
    if project_id == "default":
        project_id = f"thread-{thread_id}"

    project_cfg = cfg.for_project(project_id)
    project_cfg.ensure_dirs()
    existing = _load_session_file(project_cfg.project_root)
    now = _utc_now()
    record = ProjectSessionRecord(
        project_id=project_cfg.project_id,
        thread_id=thread_id,
        created_at=payload.created_at or existing.created_at if existing else payload.created_at or now,
        updated_at=payload.updated_at or now,
        root=str(project_cfg.project_root.resolve()),
    )
    _write_session_file(project_cfg.project_root, record)
    return record


def save_project_session_messages(
    cfg: RuntimeConfig,
    project_id: str,
    payload: ProjectSessionMessagesUpsert,
) -> ProjectSessionMessagesRecord:
    project_cfg = cfg.for_project(project_id)
    project_cfg.ensure_dirs()
    record = ProjectSessionMessagesRecord(
        project_id=project_cfg.project_id,
        messages=payload.messages,
        updated_at=payload.updated_at or _utc_now(),
    )
    _write_session_messages_file(project_cfg.project_root, record)
    return record


def load_project_session_messages(cfg: RuntimeConfig, project_id: str) -> ProjectSessionMessagesRecord:
    project_cfg = cfg.for_project(project_id)
    existing = _load_session_messages_file(project_cfg.project_root)
    if existing is not None and existing.messages:
        return ProjectSessionMessagesRecord(
            project_id=project_cfg.project_id,
            messages=existing.messages,
            updated_at=existing.updated_at,
        )
    thread_id = normalize_thread_id(project_cfg.project_id)
    if thread_id:
        history_messages = _load_conversation_history_messages(cfg, thread_id)
        if history_messages:
            return ProjectSessionMessagesRecord(
                project_id=project_cfg.project_id,
                messages=history_messages,
                updated_at=_mtime_iso(_conversation_history_path(cfg, thread_id)),
            )
    return ProjectSessionMessagesRecord(project_id=project_cfg.project_id, messages=[], updated_at=_utc_now())


def list_project_sessions(cfg: RuntimeConfig) -> list[ProjectSessionRecord]:
    projects_root = cfg.workspace_root / "projects"
    if not projects_root.exists():
        return []

    cleanup_empty_project_sessions(cfg)

    sessions: list[ProjectSessionRecord] = []
    for project_root in projects_root.iterdir():
        if not project_root.is_dir():
            continue
        record = load_project_session(cfg, project_root)
        if record is not None:
            sessions.append(record)

    return sorted(
        sessions,
        key=lambda item: (_timestamp_sort_key(item.updated_at), item.project_id),
        reverse=True,
    )


def cleanup_empty_project_sessions(cfg: RuntimeConfig) -> list[str]:
    projects_root = cfg.workspace_root / "projects"
    if not projects_root.exists():
        return []

    removed: list[str] = []
    for project_root in projects_root.iterdir():
        if not project_root.is_dir():
            continue
        record = load_project_session(cfg, project_root)
        thread_id = record.thread_id if record is not None else normalize_thread_id(project_root.name)
        if _has_project_activity(cfg, project_root, thread_id):
            continue
        shutil.rmtree(project_root, ignore_errors=True)
        removed.append(project_root.name)
    return removed


def load_project_session(cfg: RuntimeConfig, project_root: str | Path) -> ProjectSessionRecord | None:
    root = Path(project_root)
    existing = _load_session_file(root)
    if existing is not None:
        project_id = sanitize_project_id(existing.project_id or root.name)
        thread_id = normalize_thread_id(existing.thread_id) or normalize_thread_id(project_id)
        if not thread_id:
            return None
        return ProjectSessionRecord(
            project_id=project_id,
            thread_id=thread_id,
            created_at=existing.created_at,
            updated_at=existing.updated_at,
            root=str((cfg.workspace_root / "projects" / project_id).resolve()),
        )

    project_id = sanitize_project_id(root.name)
    thread_id = normalize_thread_id(project_id)
    if not thread_id:
        return None
    created_at = _created_at_from_project_id(project_id) or _mtime_iso(root)
    return ProjectSessionRecord(
        project_id=project_id,
        thread_id=thread_id,
        created_at=created_at,
        updated_at=created_at,
        root=str(root.resolve()),
    )


def normalize_thread_id(value: str | None) -> str | None:
    sanitized = sanitize_project_id(value)
    match = _PROJECT_THREAD_RE.search(sanitized)
    candidate = match.group(1) if match else sanitized.removeprefix("thread-")
    return candidate.lower() if _UUID_RE.fullmatch(candidate) else None


def _load_session_file(project_root: Path) -> ProjectSessionRecord | None:
    path = project_root / SESSION_FILENAME
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return ProjectSessionRecord.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _write_session_file(project_root: Path, record: ProjectSessionRecord) -> None:
    path = project_root / SESSION_FILENAME
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(record.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _load_session_messages_file(project_root: Path) -> ProjectSessionMessagesRecord | None:
    path = project_root / SESSION_MESSAGES_FILENAME
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return ProjectSessionMessagesRecord.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _load_conversation_history_messages(cfg: RuntimeConfig, thread_id: str) -> list[dict[str, str]]:
    path = _conversation_history_path(cfg, thread_id)
    if not path.exists():
        return []

    messages: list[dict[str, str]] = []
    current_role: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_role, current_lines
        if current_role is None:
            return
        content = "\n".join(current_lines).strip()
        if content:
            messages.append({"type": current_role, "content": content})
        current_role = None
        current_lines = []

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    for line in lines:
        match = _HISTORY_LINE_RE.match(line)
        if match:
            flush()
            label, content = match.groups()
            current_role = _HISTORY_ROLE_MAP[label]
            current_lines = [content] if content else []
            continue
        if current_role is not None:
            current_lines.append(line)
    flush()
    return messages


def _conversation_history_path(cfg: RuntimeConfig, thread_id: str) -> Path:
    return cfg.repo_root / "conversation_history" / f"{thread_id}.md"


def _write_session_messages_file(project_root: Path, record: ProjectSessionMessagesRecord) -> None:
    path = project_root / SESSION_MESSAGES_FILENAME
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(record.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _has_project_activity(cfg: RuntimeConfig, project_root: Path, thread_id: str | None) -> bool:
    if _has_artifact_files(project_root):
        return True
    messages = _load_session_messages_file(project_root)
    if messages is not None and messages.messages:
        return True
    if thread_id and _load_conversation_history_messages(cfg, thread_id):
        return True
    return _has_non_housekeeping_files(project_root)


def _has_artifact_files(project_root: Path) -> bool:
    artifact_root = project_root / "artifacts"
    if not artifact_root.exists():
        return False
    for path in artifact_root.rglob("*"):
        if path.is_file() and path.name != "manifest.json":
            return True
    return False


def _has_non_housekeeping_files(project_root: Path) -> bool:
    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(project_root)
        if len(relative.parts) == 1 and path.name in _HOUSEKEEPING_FILENAMES:
            continue
        if relative.parts == ("artifacts", "manifest.json"):
            continue
        if relative.parts == ("traces", "trace.jsonl") and _empty_file(path):
            continue
        if path.name == SESSION_MESSAGES_FILENAME:
            messages = _load_session_messages_file(project_root)
            if messages is None or not messages.messages:
                continue
        return True
    return False


def _empty_file(path: Path) -> bool:
    try:
        return path.stat().st_size == 0
    except OSError:
        return True


def _created_at_from_project_id(project_id: str) -> str | None:
    match = _PROJECT_TIMESTAMP_RE.match(project_id)
    if not match:
        return None
    date_part, time_part = match.groups()
    try:
        parsed = datetime.strptime(f"{date_part}{time_part}", "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return _iso_z(parsed)


def _mtime_iso(path: Path) -> str:
    return _iso_z(datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc))


def _utc_now() -> str:
    return _iso_z(datetime.now(timezone.utc))


def _iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _timestamp_sort_key(value: str) -> float:
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return 0.0
