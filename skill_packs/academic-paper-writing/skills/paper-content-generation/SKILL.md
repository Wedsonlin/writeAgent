# paper-content-generation

## Goal
Produce the `draft` artifact for the academic paper writing workflow stage `content_generation`.

## Inputs
The Agent prepares a JSON input file containing upstream artifact content and task instructions.

## Outputs
The script writes a JSON output file. The Agent then records it with `update_artifact_manifest` and advances the ProgressLedger with `update_progress`.

## Usage

```text
python skill_packs/academic-paper-writing/skills/paper-content-generation/scripts/run.py --input path/to/input.json --output path/to/output.json
```

The script is deterministic and does not call an LLM.
