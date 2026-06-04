"""Discovery of local writeAgent Skills from ``skills/*/SKILL.md``."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .skill_contracts import load_skill_contract, render_contract_for_prompt
from .types import SkillSpec


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(?P<body>.*?)\n---\s*\n?", re.DOTALL)


class SkillRegistry:
    """In-memory registry built from local Skill folders."""

    def __init__(self, specs: list[SkillSpec]) -> None:
        self._specs = sorted(specs, key=lambda item: item.name)
        self._by_name = {spec.name: spec for spec in self._specs}

    @classmethod
    def from_skills_dir(cls, skills_dir: Path) -> "SkillRegistry":
        """Scan ``skills_dir`` for ``SKILL.md`` files.

        Directories beginning with ``_`` are treated as shared support packages,
        not user-callable Skills.
        """
        root = Path(skills_dir)
        specs: list[SkillSpec] = []
        if not root.exists():
            return cls(specs)

        for skill_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            if skill_dir.name.startswith("_"):
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            raw = skill_md.read_text(encoding="utf-8")
            frontmatter, body = _split_frontmatter(raw)
            name = str(frontmatter.get("name") or skill_dir.name).strip()
            description = _extract_description(frontmatter, body)
            entrypoint = skill_dir / "scripts" / "run.py"
            contract = load_skill_contract(skill_dir, frontmatter)
            specs.append(
                SkillSpec(
                    name=name,
                    path=skill_dir,
                    description=description,
                    entrypoint=entrypoint,
                    raw_markdown=raw,
                    metadata=frontmatter,
                    contract=contract,
                    entrypoint_exists=entrypoint.exists(),
                )
            )
        return cls(specs)

    def list_specs(self) -> list[SkillSpec]:
        """Return all discovered Skill specs, including non-executable skeletons."""
        return list(self._specs)

    def list_executable_specs(self) -> list[SkillSpec]:
        """Return only Skills with a local ``scripts/run.py`` entrypoint."""
        return [spec for spec in self._specs if spec.entrypoint_exists]

    def get(self, skill_name: str) -> SkillSpec:
        """Look up a Skill by name."""
        try:
            return self._by_name[skill_name]
        except KeyError as exc:
            available = ", ".join(self._by_name) or "<none>"
            raise KeyError(f"Unknown skill '{skill_name}'. Available: {available}") from exc

    def render_for_prompt(self) -> str:
        """Render the registry as a compact LLM-readable tool catalog."""
        if not self._specs:
            return "No local skills were discovered."

        lines = [
            "Local Skill Registry:",
            "Only call run_skill for entries marked executable=true.",
        ]
        for spec in self._specs:
            status = "true" if spec.entrypoint_exists else "false"
            lines.append(f"- name: {spec.name}")
            lines.append(f"  executable: {status}")
            lines.append(f"  description: {_one_line(spec.description)}")
            lines.extend(render_contract_for_prompt(spec.contract))
        return "\n".join(lines)


def _split_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        return {}, raw

    frontmatter_raw = match.group("body")
    body = raw[match.end() :]
    try:
        import yaml

        parsed = yaml.safe_load(frontmatter_raw) or {}
        if isinstance(parsed, dict):
            return parsed, body
    except Exception:
        pass
    return _parse_simple_frontmatter(frontmatter_raw), body


def _parse_simple_frontmatter(text: str) -> dict[str, Any]:
    """Small fallback parser for the simple key/value frontmatter used here."""
    data: dict[str, Any] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip("'\"")
    return data


def _extract_description(frontmatter: dict[str, Any], body: str) -> str:
    frontmatter_description = frontmatter.get("description")
    if isinstance(frontmatter_description, str) and frontmatter_description.strip():
        return frontmatter_description.strip()

    sections = []
    for para in re.split(r"\n\s*\n", body):
        cleaned = _clean_markdown(para)
        if cleaned:
            sections.append(cleaned)
        if len(sections) >= 3:
            break
    return "\n".join(sections)[:1200] or "No description provided."


def _clean_markdown(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("```"):
            continue
        stripped = stripped.lstrip("#").strip()
        stripped = stripped.lstrip(">- ").strip()
        if stripped:
            lines.append(stripped)
    return " ".join(lines)


def _one_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
