# Search Strategy

Use this file only when seed references do not adequately cover the task book, research keywords, core arguments, and innovation points.

## Query Construction

Build 2-5 concise academic queries from:

- The task book topic and research direction keywords.
- Each uncovered core argument.
- Each uncovered innovation point.
- Important method or domain phrases from `research_scope.subtopics`.
- Evidence needs from `task_book_sections.argument_evidence_matrix`.

Prefer English academic terms for international literature and Chinese terms when the target venue or task book is Chinese-domain specific.

## Search And Extraction

- Call `search_knowledge` with `intent="academic_papers"`.
- Prefer papers, preprints, proceedings pages, DOI pages, publisher pages, and arXiv records.
- Call `extract_sources` for selected URLs before using paper claims, abstracts, or methodology statements.
- Treat search snippets as candidate evidence only. Do not mark snippet-only evidence as `strong` or `moderate`.

## Selection And Deduplication

Keep sources that:

- Directly support, extend, or challenge a core argument.
- Directly support, extend, or challenge an innovation point.
- Explain a field theme, method family, controversy, or gap.
- Provide citation metadata useful for GB/T 7714 or APA.

Deduplicate by DOI first, then arXiv id, then normalized title. Preserve the most complete metadata record.

## Extra References

Add selected supplemental papers to `extra_references` with:

```json
{
  "type": "paper",
  "id": "stable-paper-key",
  "title": "...",
  "authors": ["..."],
  "year": 2024,
  "venue": "...",
  "doi": null,
  "url": "...",
  "abstract": "...",
  "source_kind": "search_evidence"
}
```

Also create `paper_reading_cards[]` for selected supplemental papers before adding them to support matrices. Do not invent missing DOI, venue, page ranges, or findings.
