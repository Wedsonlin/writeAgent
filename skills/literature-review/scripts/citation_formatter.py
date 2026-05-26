"""Format paper records as GB/T 7714-2015 and APA 7 reference strings.

The two standards differ in three high-impact ways for our use case:

1. **Author list separator** — GB/T 7714 uses commas between authors and ends
   the author block with "等" (3+ authors) or no terminator; APA uses "&"
   before the last author.
2. **Title case** — GB/T 7714 keeps original case + appends a `[type]` tag
   (e.g. ``[J]``, ``[C]``, ``[D]``); APA uses sentence case + italicises titles.
3. **Field order** — GB/T 7714: ``author. title[type]. venue, year, vol(issue): pages.``;
   APA: ``Author, A. (year). title. Venue, vol(issue), pages.``

This module is intentionally pragmatic: it produces standards-conformant strings
for the vast majority of common entries (journal, conference, preprint, book)
without claiming to handle every edge case in either spec.
"""

from __future__ import annotations

from typing import Any


GB_TYPE_TAG = {
    "journal": "J",
    "conference": "C",
    "book": "M",
    "thesis": "D",
    "report": "R",
    "preprint": "EB/OL",
    "misc": "Z",
}


# --------------------------------------------------------------------------- #
# GB/T 7714-2015
# --------------------------------------------------------------------------- #


def format_gb7714(paper: dict[str, Any]) -> str:
    authors = paper.get("authors", []) or []
    author_block = _gb_authors(authors)
    title = (paper.get("title") or "").strip()
    type_tag = GB_TYPE_TAG.get(paper.get("type", "misc"), "Z")
    venue = (paper.get("venue") or "").strip()
    year = paper.get("year") or 0
    doi = paper.get("doi")
    url = paper.get("url")

    parts: list[str] = []
    if author_block:
        parts.append(f"{author_block}.")
    parts.append(f"{title}[{type_tag}].")
    if venue:
        if year:
            parts.append(f"{venue}, {year}.")
        else:
            parts.append(f"{venue}.")
    else:
        if year:
            parts.append(f"{year}.")
    if doi:
        parts.append(f"DOI:{doi}.")
    elif url:
        parts.append(f"({url}).")
    return " ".join(p for p in parts if p)


def _gb_authors(authors: list[str]) -> str:
    if not authors:
        return ""
    formatted = [_gb_one_author(a) for a in authors[:3]]
    if len(authors) > 3:
        return ", ".join(formatted) + ", 等"
    return ", ".join(formatted)


def _gb_one_author(name: str) -> str:
    """Convert "First Last" or "Last, First" into GB/T 7714 "Last F"."""
    name = name.strip()
    if not name:
        return ""
    if "," in name:
        last, _, first = name.partition(",")
        last = last.strip()
        first = first.strip()
    else:
        parts = name.split()
        if not parts:
            return name
        last = parts[-1]
        first = " ".join(parts[:-1])
    initials = "".join(p[0].upper() for p in first.split() if p)
    return f"{last} {initials}" if initials else last


# --------------------------------------------------------------------------- #
# APA 7
# --------------------------------------------------------------------------- #


def format_apa(paper: dict[str, Any]) -> str:
    authors = paper.get("authors", []) or []
    author_block = _apa_authors(authors)
    year = paper.get("year") or "n.d."
    title = (paper.get("title") or "").strip().rstrip(".")
    venue = (paper.get("venue") or "").strip()
    doi = paper.get("doi")
    url = paper.get("url")
    ptype = paper.get("type", "misc")

    parts: list[str] = []
    if author_block:
        parts.append(f"{author_block} ({year}).")
    else:
        parts.append(f"({year}).")
    if ptype in ("journal", "conference"):
        parts.append(f"{title}.")
        if venue:
            parts.append(f"*{venue}*.")
    elif ptype == "preprint":
        parts.append(f"*{title}*.")
        if venue:
            parts.append(f"{venue}.")
    else:
        parts.append(f"*{title}*.")
        if venue:
            parts.append(f"{venue}.")
    if doi:
        parts.append(f"https://doi.org/{doi}")
    elif url:
        parts.append(url)
    return " ".join(p for p in parts if p)


def _apa_authors(authors: list[str]) -> str:
    if not authors:
        return ""
    parts = [_apa_one_author(a) for a in authors]
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} & {parts[1]}"
    if len(parts) <= 20:
        return ", ".join(parts[:-1]) + f", & {parts[-1]}"
    return ", ".join(parts[:19]) + ", ... " + parts[-1]


def _apa_one_author(name: str) -> str:
    name = name.strip()
    if not name:
        return ""
    if "," in name:
        last, _, first = name.partition(",")
        last = last.strip()
        first = first.strip()
    else:
        bits = name.split()
        if not bits:
            return name
        last = bits[-1]
        first = " ".join(bits[:-1])
    initials = ". ".join(p[0].upper() for p in first.split() if p)
    return f"{last}, {initials}." if initials else last
