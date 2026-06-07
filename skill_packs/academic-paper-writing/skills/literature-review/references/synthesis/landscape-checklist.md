# Literature Landscape Checklist

Before running the script, check:

- Every reference in `references_seed` has a `source_map` entry or is intentionally left unmapped.
- Every `source_map.paper_id` matches a BibTeX key.
- Each `key_claims[]` item is concise enough to support later outline and drafting.
- `alignment_to_core[].core_argument_index` refers to a real core argument.
- Clusters are theme-based and include at least one paper.
- `consensus`, `controversies`, and `research_gaps` are not duplicates of cluster summaries.
- Low-confidence claims are marked with `evidence_strength: weak`.
- Missing DOI or URL is left null, not invented.
