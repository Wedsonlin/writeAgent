# Writing Task Final Checklist

Run this checklist before executing `scripts/run.py`.

- `argument_brief.core_claim` states what the paper shows, not only what it builds.
- `argument_brief.contributions[]` contains concrete contributions.
- `argument_brief.core_arguments[]` exists when the thesis claims differ from contribution wording.
- `argument_brief.venue.paper_type` is one of `system`, `survey`, `empirical`, or `theoretical`.
- `argument_brief.venue.journal` or equivalent venue name is present.
- `argument_brief.venue.word_limit` is present.
- `argument_brief.scope.boundary` says what is out of scope.
- `references_seed[]` points to available reference material when literature review should run next.
- `provenance` distinguishes confirmed facts from inferred defaults.

If any critical item is missing, call `ask_user` before running the script.
