# literature-review

## Goal
Produce the `literature_report` artifact for the academic paper writing workflow stage `literature_review`.

## Inputs
The Agent prepares a JSON input file containing upstream artifact content and task instructions.

## Outputs
The script writes a JSON output file. The Agent then records it with `update_artifact_manifest` and advances the ProgressLedger with `update_progress`.

## Usage

```text
python skill_packs/academic-paper-writing/skills/literature-review/scripts/run.py --input path/to/input.json --output path/to/output.json
```

The script is deterministic and does not call an LLM.
