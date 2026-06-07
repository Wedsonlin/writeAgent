# APA Formatting Rules

The script implements a compact deterministic APA-like entry for artifact use.

Format:

```text
Family, I. (Year). Title. Venue. DOI-or-URL
```

Rules:

- Use `n.d.` when the year is missing.
- Preserve title casing from BibTeX metadata.
- Include DOI as `https://doi.org/...` when present.
- Include URL only when DOI is absent.
- Do not synthesize issue, volume, page range, or publisher fields when absent.
