# polish-and-plagiarism

## Goal
Produce the `polished_draft` artifact for the academic paper writing workflow stage `polish_and_plagiarism`.

## Inputs
The Agent prepares a JSON input file containing upstream artifact content and task instructions.

## Outputs
The script writes a JSON output file. The Agent then records it with `update_artifact_manifest` and advances the ProgressLedger with `update_progress`.

## Usage

```text
python skill_packs/academic-paper-writing/skills/polish-and-plagiarism/scripts/run.py --input path/to/input.json --output path/to/output.json
```

The script is deterministic and does not call an LLM.
