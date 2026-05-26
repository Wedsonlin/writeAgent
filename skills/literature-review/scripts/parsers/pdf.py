"""PDF → RawPaper list.

We only extract the first 2 pages, which is enough to read the title, authors
and (usually) abstract. If the PDF is a pure scan with no text layer we emit a
record with title derived from the filename and ``evidence_strength = "anecdotal"``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any


def parse_pdf_dir(directory: str | Path) -> list[dict[str, Any]]:
    base = Path(directory)
    if not base.exists():
        print(f"[parsers.pdf] WARN: directory not found: {base}", file=sys.stderr)
        return []
    out: list[dict[str, Any]] = []
    for pdf in sorted(base.rglob("*.pdf")):
        try:
            out.append(parse_pdf_file(pdf))
        except Exception as exc:  # noqa: BLE001
            print(f"[parsers.pdf] WARN: cannot parse {pdf}: {exc}", file=sys.stderr)
    return out


def parse_pdf_file(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    text = _extract_first_pages(p, max_pages=2)
    if not text:
        return _from_filename_only(p)

    title = _guess_title(text) or p.stem.replace("_", " ")
    authors = _guess_authors(text)
    abstract = _guess_abstract(text)
    year = _guess_year(text)

    return {
        "id": _safe_id(p.stem),
        "type": "preprint",
        "title": title,
        "authors": authors,
        "year": year,
        "venue": None,
        "doi": _guess_doi(text),
        "url": None,
        "abstract": abstract,
        "source_kind": "pdf",
    }


# --------------------------------------------------------------------------- #
# extraction helpers
# --------------------------------------------------------------------------- #


def _extract_first_pages(path: Path, max_pages: int = 2) -> str:
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ImportError:
        print(
            "[parsers.pdf] pypdf is not installed; skipping PDF body extraction.",
            file=sys.stderr,
        )
        return ""
    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # noqa: BLE001
        print(f"[parsers.pdf] cannot open {path}: {exc}", file=sys.stderr)
        return ""

    chunks: list[str] = []
    for page in reader.pages[:max_pages]:
        try:
            chunks.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001
            continue
    return "\n".join(chunks)


_TITLE_LINE_RE = re.compile(r"^[\w\dA-Za-z\-:,.\s]{8,120}$")


def _guess_title(text: str) -> str | None:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith(("abstract", "keywords", "1 introduction")):
            return None
        if _TITLE_LINE_RE.match(line) and not line.endswith("."):
            return line
    return None


def _guess_authors(text: str) -> list[str]:
    # Crude heuristic: line that contains commas + "and" / "&" right after the title.
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in lines[:8]:
        if ("," in ln or "&" in ln or " and " in ln) and not ln.lower().startswith(
            ("abstract", "keywords")
        ):
            parts = re.split(r",|&| and ", ln)
            authors = [p.strip() for p in parts if 2 <= len(p.strip()) <= 40]
            if 2 <= len(authors) <= 12:
                return authors
    return []


def _guess_abstract(text: str) -> str | None:
    lower = text.lower()
    idx = lower.find("abstract")
    if idx == -1:
        return None
    end_idx = lower.find("introduction", idx + 8)
    if end_idx == -1:
        end_idx = idx + 2000
    snippet = text[idx + 8 : end_idx].strip()
    # Trim leading punctuation / line break
    snippet = re.sub(r"^[\W_]+", "", snippet).strip()
    return snippet[:1500] or None


_YEAR_RE = re.compile(r"\b(19[8-9]\d|20\d{2})\b")


def _guess_year(text: str) -> int:
    match = _YEAR_RE.search(text)
    return int(match.group(0)) if match else 0


_DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s]+", re.IGNORECASE)


def _guess_doi(text: str) -> str | None:
    match = _DOI_RE.search(text)
    return match.group(0).rstrip(".,;)") if match else None


def _safe_id(stem: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "-", stem.lower())[:64] or "pdf-unknown"


def _from_filename_only(p: Path) -> dict[str, Any]:
    return {
        "id": _safe_id(p.stem),
        "type": "preprint",
        "title": p.stem.replace("_", " "),
        "authors": [],
        "year": 0,
        "venue": None,
        "doi": None,
        "url": None,
        "abstract": None,
        "source_kind": "pdf",
    }
