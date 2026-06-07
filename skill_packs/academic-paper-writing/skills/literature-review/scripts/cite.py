from __future__ import annotations

from typing import Any


def format_bibliography(papers: list[dict[str, Any]]) -> dict[str, list[str]]:
    return {
        "gb7714": [_format_gb7714(paper) for paper in papers],
        "apa": [_format_apa(paper) for paper in papers],
    }


def _format_gb7714(paper: dict[str, Any]) -> str:
    authors = _gb_authors(paper.get("authors", []))
    mark = _gb_mark(str(paper.get("type") or "misc"))
    title = paper.get("title") or "Untitled"
    venue = paper.get("venue") or "Unknown venue"
    year = paper.get("year") or "n.d."
    suffix = ""
    if paper.get("doi"):
        suffix += f" DOI:{paper['doi']}."
    elif paper.get("url"):
        suffix += f" ({paper['url']})."
    return f"{authors}. {title}{mark}. {venue}, {year}.{suffix}".replace("..", ".")


def _format_apa(paper: dict[str, Any]) -> str:
    authors = _apa_authors(paper.get("authors", []))
    year = paper.get("year") or "n.d."
    title = paper.get("title") or "Untitled"
    venue = paper.get("venue") or "Unknown venue"
    suffix = ""
    if paper.get("doi"):
        suffix = f" https://doi.org/{paper['doi']}"
    elif paper.get("url"):
        suffix = f" {paper['url']}"
    return f"{authors} ({year}). {title}. {venue}.{suffix}".strip()


def _gb_mark(paper_type: str) -> str:
    if paper_type == "conference":
        return "[C]"
    if paper_type == "journal":
        return "[J]"
    if paper_type == "preprint":
        return "[EB/OL]"
    return "[Z]"


def _gb_authors(authors: list[str]) -> str:
    if not authors:
        return "Unknown"
    shown = [_family_first(author) for author in authors[:3]]
    if len(authors) > 3:
        return ", ".join(shown) + ", 等"
    return ", ".join(shown)


def _apa_authors(authors: list[str]) -> str:
    if not authors:
        return "Unknown"
    if len(authors) > 20:
        authors = authors[:19] + [authors[-1]]
    return ", ".join(_apa_name(author) for author in authors)


def _family_first(author: str) -> str:
    parts = author.split()
    if not parts:
        return author
    if len(parts) == 1:
        return parts[0]
    return f"{parts[-1]} {' '.join(parts[:-1])}"


def _apa_name(author: str) -> str:
    parts = author.split()
    if len(parts) <= 1:
        return author
    family = parts[-1]
    initials = " ".join(f"{part[0]}." for part in parts[:-1] if part)
    return f"{family}, {initials}"
