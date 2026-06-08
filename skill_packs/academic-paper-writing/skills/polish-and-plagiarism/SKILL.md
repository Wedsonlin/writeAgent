# polish-and-plagiarism

## Goal
Produce the `polished_draft` artifact for the academic paper writing workflow stage `polish_and_plagiarism`.

## Inputs
The Agent prepares a JSON input file containing `polished_markdown`, polish notes, protected claims, citation constraints, and similarity-reduction requirements. Do not pass only `artifact_ref`; the script validates and writes the final artifact but does not invent missing prose.

## Outputs
The script writes a JSON output file and a final Markdown sidecar file next to it. The Agent then records it with `update_artifact_manifest` and advances the ProgressLedger with `update_progress`.

## Usage

```text
python skill_packs/academic-paper-writing/skills/polish-and-plagiarism/scripts/run.py --input path/to/input.json --output path/to/output.json
```

The script is deterministic and does not call an LLM.
