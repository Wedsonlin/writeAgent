"""Reference parsers — convert BibTeX/PDF/text into a uniform RawPaper dict.

Each parser returns a list of dicts shaped like::

    {
      "id": "smith2024llmagents",
      "type": "journal" | "conference" | "preprint" | ...,
      "title": "...",
      "authors": ["Last, First", ...],
      "year": 2024,
      "venue": "...",
      "doi": "10.xxx/xxx" or None,
      "url": "https://..." or None,
      "abstract": "..." or None,
      "source_kind": "bibtex" | "pdf" | "text",
    }
"""
