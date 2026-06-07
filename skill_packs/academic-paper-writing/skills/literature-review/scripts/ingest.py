from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import bibtexparser

from validate import ContractError


def ingest_references(data: dict[str, Any], input_dir: Path) -> list[dict[str, Any]]:
    task = data.get("writing_task", {})
    seeds = list(task.get("references_seed", [])) + list(data.get("extra_references", []))
    papers: list[dict[str, Any]] = []
    for seed in seeds:
        if not isinstance(seed, dict):
            continue
        source_type = seed.get("type")
        if source_type == "bibtex":
            papers.extend(_read_bibtex(seed, input_dir))
        elif source_type in {"text", "pdf"}:
            papers.append(_placeholder_paper(seed))
    return papers


def _read_bibtex(seed: dict[str, Any], input_dir: Path) -> list[dict[str, Any]]:
    path = _resolve_path(str(seed.get("path") or ""), input_dir)
    if path is None:
        raise ContractError("bibtex reference file does not exist", [str(seed.get("path"))])
    database = bibtexparser.loads(path.read_text(encoding="utf-8"))
    return [_entry_to_paper(entry) for entry in database.entries]


def _resolve_path(raw: str, input_dir: Path) -> Path | None:
    candidate = Path(raw)
    candidates = [candidate] if candidate.is_absolute() else [Path.cwd() / candidate, input_dir / candidate]
    for item in candidates:
        if item.exists():
            return item
    return None


def _entry_to_paper(entry: dict[str, Any]) -> dict[str, Any]:
    venue = entry.get("journal") or entry.get("booktitle") or entry.get("howpublished") or entry.get("publisher") or ""
    return {
        "id": _clean(entry.get("ID") or entry.get("id") or ""),
        "type": _paper_type(entry.get("ENTRYTYPE"), venue),
        "title": _clean(entry.get("title") or ""),
        "authors": _authors(entry.get("author") or ""),
        "year": _year(entry.get("year")),
        "venue": _clean(venue),
        "doi": _clean(entry.get("doi")) or None,
        "url": _clean(entry.get("url")) or None,
        "abstract": _clean(entry.get("abstract") or ""),
        "source_kind": "bibtex",
    }


def _placeholder_paper(seed: dict[str, Any]) -> dict[str, Any]:
    raw = seed.get("raw") or seed.get("path") or seed.get("id") or "unmapped-reference"
    return {
        "id": str(seed.get("id") or raw),
        "type": str(seed.get("type") or "misc"),
        "title": str(raw),
        "authors": [],
        "year": seed.get("year"),
        "venue": "",
        "doi": None,
        "url": None,
        "abstract": "",
        "source_kind": str(seed.get("type") or "seed"),
    }


def _paper_type(entry_type: Any, venue: str) -> str:
    entry = str(entry_type or "").lower()
    lower_venue = venue.lower()
    if "arxiv" in lower_venue:
        return "preprint"
    if entry == "inproceedings":
        return "conference"
    if entry == "article":
        return "journal"
    return entry or "misc"


def _authors(raw: str) -> list[str]:
    if not raw:
        return []
    return [_clean(part) for part in raw.split(" and ") if _clean(part)]


def _year(raw: Any) -> int | None:
    match = re.search(r"\d{4}", str(raw or ""))
    return int(match.group(0)) if match else None


def _clean(value: Any) -> str:
    text = str(value or "")
    replacements = {
        "{": "",
        "}": "",
        "\\`": "",
        "\\'": "",
        '\\"': "",
        "\\&": "&",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return " ".join(text.split())
