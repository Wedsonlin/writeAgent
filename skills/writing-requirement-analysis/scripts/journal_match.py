"""Lookup a journal style profile from references/journal-styles.md.

The reference file embeds a tiny YAML table at the top; we parse just that
block so contributors can edit profiles without touching code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


REFS_DIR = Path(__file__).resolve().parent.parent / "references"
STYLE_FILE = REFS_DIR / "journal-styles.md"


_DEFAULT_PROFILE: dict[str, str] = {
    "citation_style": "GB/T 7714",
    "tone": "formal-zh",
    "structure_hint": "摘要-引言-相关工作-方法/系统-实验/分析-讨论-结论-参考文献",
}


def _load_profiles() -> dict[str, dict[str, str]]:
    if yaml is None or not STYLE_FILE.exists():
        return {"default": _DEFAULT_PROFILE}
    text = STYLE_FILE.read_text(encoding="utf-8")
    # The YAML block sits between two ``` fences right after a `## YAML 索引` heading.
    marker = "```yaml"
    start = text.find(marker)
    if start == -1:
        return {"default": _DEFAULT_PROFILE}
    end = text.find("```", start + len(marker))
    if end == -1:
        return {"default": _DEFAULT_PROFILE}
    block = text[start + len(marker) : end]
    data = yaml.safe_load(block) or {}
    if not isinstance(data, dict):
        return {"default": _DEFAULT_PROFILE}
    return {str(k): v for k, v in data.items()}


def match_journal_style(name: str, level: str | None = None) -> dict[str, Any]:
    """Return the best-fit style profile for ``name`` (case-insensitive substring)."""
    profiles = _load_profiles()
    if not name or name == "未指定":
        return profiles.get("default", _DEFAULT_PROFILE)

    name_lower = name.lower()
    for key, profile in profiles.items():
        if key == "default":
            continue
        if key.lower() in name_lower or name_lower in key.lower():
            return profile

    # Fallback by level
    if level:
        level_key = f"level::{level}"
        if level_key in profiles:
            return profiles[level_key]

    return profiles.get("default", _DEFAULT_PROFILE)
