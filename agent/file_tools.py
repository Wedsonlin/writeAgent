"""Safe workspace-scoped file reading helpers for agent tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any


DEFAULT_MAX_CHARS = 20000


def read_workspace_file(
    path: str,
    *,
    workspace_root: Path,
    allowed_refs: list[str] | None = None,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> dict[str, Any]:
    """Read a text file under ``workspace_root`` with optional exact allowlist."""
    try:
        target = resolve_workspace_path(path, workspace_root=workspace_root)
    except ValueError as exc:
        return _error(path, "fatal", str(exc))

    if allowed_refs is not None:
        try:
            allowed_paths = {
                resolve_workspace_path(ref, workspace_root=workspace_root)
                for ref in allowed_refs
            }
        except ValueError as exc:
            return _error(path, "fatal", f"Invalid allowed file ref: {exc}")
        if target not in allowed_paths:
            return _error(
                path,
                "fatal",
                "File path is not authorized for this agent.",
                allowed_refs=allowed_refs,
            )

    if not target.exists():
        return _error(path, "error", "File does not exist.", resolved_path=str(target))
    if not target.is_file():
        return _error(path, "error", "Path is not a file.", resolved_path=str(target))

    limit = max(0, int(max_chars or DEFAULT_MAX_CHARS))
    text = target.read_text(encoding="utf-8", errors="replace")
    truncated = len(text) > limit
    content = text[:limit] if truncated else text
    return {
        "tool": "read_workspace_file",
        "status": "ok",
        "path": str(target),
        "content": content,
        "chars": len(text),
        "returned_chars": len(content),
        "truncated": truncated,
    }


def resolve_workspace_path(path: str, *, workspace_root: Path) -> Path:
    """Resolve a path and ensure it remains under ``workspace_root``."""
    if not str(path or "").strip():
        raise ValueError("File path is required.")

    root = Path(workspace_root).resolve()
    raw_path = Path(path)
    candidate = raw_path if raw_path.is_absolute() else root / raw_path
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"File path escapes workspace: {path}") from exc
    return resolved


def validate_workspace_file_ref(path: str, *, workspace_root: Path) -> str | None:
    """Return an error string if a file ref is unsafe or not an existing file."""
    try:
        resolved = resolve_workspace_path(path, workspace_root=workspace_root)
    except ValueError as exc:
        return str(exc)
    if not resolved.exists():
        return f"File ref does not exist: {path}"
    if not resolved.is_file():
        return f"File ref is not a file: {path}"
    return None


def _error(path: str, status: str, message: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "tool": "read_workspace_file",
        "status": status,
        "path": path,
        "error": message,
    }
    payload.update(extra)
    return payload


__all__ = [
    "DEFAULT_MAX_CHARS",
    "read_workspace_file",
    "resolve_workspace_path",
    "validate_workspace_file_ref",
]
