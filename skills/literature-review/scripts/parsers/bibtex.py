"""BibTeX → RawPaper list.

Uses ``bibtexparser`` (1.x API). Maps BibTeX entry types into our schema's
``type`` enum (journal / conference / preprint / book / thesis / report / misc).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any


_ENTRY_TYPE_MAP = {
    "article": "journal",
    "inproceedings": "conference",
    "conference": "conference",
    "proceedings": "conference",
    "book": "book",
    "incollection": "book",
    "phdthesis": "thesis",
    "mastersthesis": "thesis",
    "techreport": "report",
    "manual": "report",
    "unpublished": "preprint",
    "misc": "misc",
}


def parse_bibtex_file(path: str | Path) -> list[dict[str, Any]]:
    """Parse a single .bib file."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return parse_bibtex_text(text)


def parse_bibtex_text(text: str) -> list[dict[str, Any]]:
    """Parse a BibTeX-encoded string. Falls back to a regex if bibtexparser missing."""
    try:
        import bibtexparser  # type: ignore[import-not-found]
        from bibtexparser.bparser import BibTexParser  # type: ignore[import-not-found]
    except ImportError:
        print(
            "[parsers.bibtex] bibtexparser not installed; using fallback regex parser.",
            file=sys.stderr,
        )
        return _fallback_regex_parse(text)

    parser = BibTexParser(common_strings=True)
    parser.ignore_nonstandard_types = False
    db = bibtexparser.loads(text, parser=parser)
    out: list[dict[str, Any]] = []
    for entry in db.entries:
        out.append(_normalize_entry(entry))
    return out


def _normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    entry_type = (entry.get("ENTRYTYPE") or "misc").lower()
    paper_type = _ENTRY_TYPE_MAP.get(entry_type, "misc")
    if entry.get("eprinttype", "").lower() == "arxiv" or "arxiv" in entry.get("journal", "").lower():
        paper_type = "preprint"

    venue = (
        entry.get("journal")
        or entry.get("booktitle")
        or entry.get("howpublished")
        or entry.get("school")
        or entry.get("institution")
        or ""
    )

    authors_raw = entry.get("author", "")
    authors = _split_authors(authors_raw)

    year_str = entry.get("year", "0")
    try:
        year = int(re.search(r"\d{4}", year_str).group(0)) if re.search(r"\d{4}", year_str) else 0
    except Exception:
        year = 0

    url = entry.get("url") or (f"https://doi.org/{entry['doi']}" if entry.get("doi") else None)

    return {
        "id": entry.get("ID") or f"bib-{abs(hash(entry.get('title', '')))%10_000_000}",
        "type": paper_type,
        "title": _clean(entry.get("title", "")),
        "authors": authors,
        "year": year,
        "venue": _clean(venue),
        "doi": entry.get("doi"),
        "url": url,
        "abstract": _clean(entry.get("abstract", "")) or None,
        "source_kind": "bibtex",
    }


def _split_authors(raw: str) -> list[str]:
    if not raw:
        return []
    # BibTeX uses " and " as the separator.
    parts = [p.strip() for p in re.split(r"\s+and\s+", raw) if p.strip()]
    return [_clean(p) for p in parts]


_ACCENT_RE = re.compile(r"""\\['`"^~=.](?:\{?([a-zA-Z])\}?|([a-zA-Z]))""")


def _clean(text: str) -> str:
    if not text:
        return ""
    # Strip LaTeX accent escapes ( \`i  ->  i ,  \'e -> e , \"o -> o , etc.).
    out = _ACCENT_RE.sub(lambda m: m.group(1) or m.group(2) or "", text)
    # Strip remaining braces and basic commands.
    out = re.sub(r"\{|\}", "", out)
    out = re.sub(r"\\[a-zA-Z]+\s?", "", out)
    return out.strip()


# --------------------------------------------------------------------------- #
# Fallback when bibtexparser is unavailable (e.g. read-only OpenClaw sandbox)
# --------------------------------------------------------------------------- #


_ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,]+),(.*?)\n\}", re.DOTALL)


def _fallback_regex_parse(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for match in _ENTRY_RE.finditer(text):
        entry_type = match.group(1).lower()
        key = match.group(2).strip()
        body = match.group(3)
        fields: dict[str, str] = {}
        for field_match in re.finditer(
            r"(\w+)\s*=\s*[\{\"](.+?)[\}\"]\s*,?\s*\n", body + "\n", re.DOTALL
        ):
            fields[field_match.group(1).lower()] = field_match.group(2).strip()
        synthetic = {"ENTRYTYPE": entry_type, "ID": key, **fields}
        out.append(_normalize_entry(synthetic))
    return out
