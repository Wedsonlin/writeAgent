# paper-content-generation

## Goal
Produce the `draft` artifact for the academic paper writing workflow stage `content_generation`.

## Inputs
The Agent prepares a JSON input file containing a complete LLM-authored `draft` object, upstream artifact content, and task instructions. Do not pass only `artifact_ref`; the script validates and packages prose but does not invent the paper body.

Required draft fields:

- `title`
- `abstract`
- `keywords`
- `sections[].title`
- `sections[].content_markdown`
- `sections[].citations_used`
- `references`

## Outputs
The script writes a JSON output file. The Agent then records it with `update_artifact_manifest` and advances the ProgressLedger with `update_progress`.

## Usage

```text
python skill_packs/academic-paper-writing/skills/paper-content-generation/scripts/run.py --input path/to/input.json --output path/to/output.json
```

The script is deterministic and does not call an LLM.
