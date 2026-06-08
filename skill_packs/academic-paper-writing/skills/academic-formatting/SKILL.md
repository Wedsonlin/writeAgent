# academic-formatting

## Goal
Produce the `formatted_draft` artifact for the academic paper writing workflow stage `academic_formatting`.

## Inputs
The Agent prepares a JSON input file containing the full `draft` object, formatting constraints, and export requirements. Do not pass only `artifact_ref`.

## Outputs
The script writes a JSON output file and a Markdown sidecar file next to it. The Agent then records it with `update_artifact_manifest` and advances the ProgressLedger with `update_progress`.

## Usage

```text
python skill_packs/academic-paper-writing/skills/academic-formatting/scripts/run.py --input path/to/input.json --output path/to/output.json
```

The script is deterministic and does not call an LLM.
