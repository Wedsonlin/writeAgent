"""Workspace path boundary helpers."""

from __future__ import annotations

from pathlib import Path


class WorkspaceBoundaryError(ValueError):
    """Raised when a path escapes the configured workspace boundary."""


def resolve_allowed_path(path: str | Path | None, *, default: Path, allowed_roots: list[Path]) -> Path:
    candidate = Path(path).expanduser() if path is not None else default
    if not candidate.is_absolute():
        candidate = default / candidate
    resolved = candidate.resolve()
    if not is_within_allowed_roots(resolved, allowed_roots):
        roots = ", ".join(str(root.resolve()) for root in allowed_roots)
        raise WorkspaceBoundaryError(f"Path is outside allowed roots: {resolved}. Allowed roots: {roots}")
    return resolved


def is_within_allowed_roots(path: str | Path, allowed_roots: list[Path]) -> bool:
    resolved = Path(path).resolve()
    for root in allowed_roots:
        root_resolved = Path(root).resolve()
        if resolved == root_resolved or root_resolved in resolved.parents:
            return True
    return False
