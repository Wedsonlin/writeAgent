# Target Template Interpretation

Use this guide when the user provides a journal, school, or course formatting template.

## Priority

1. Explicit user/template requirements.
2. `formatting_constraints` in the input JSON.
3. Target journal style profile from upstream artifacts.
4. Skill5 defaults: Chinese academic layout, GB/T 7714 references, numeric `[n]` citations.

## What Skill5 May Change

- Heading levels and heading text presentation.
- Abstract and keyword block placement.
- In-text citation marker shape when it can be mapped to `references[]`.
- Reference entry rendering when structured metadata is present.
- Figure/table numbering and caption placement.
- DOCX/PDF export styling.

## What Skill5 Must Not Change

- Core arguments, evidence interpretation, conclusions, or section meaning.
- Citation provenance or source identity.
- Research data, metrics, experiments, or literature claims.
- Paragraph wording beyond mechanical citation/heading normalization.

When a template requirement conflicts with preserving meaning or citations, preserve meaning and record a warning in `issues[]`.
