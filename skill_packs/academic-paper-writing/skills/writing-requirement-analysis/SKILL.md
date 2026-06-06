# writing-requirement-analysis

## Goal
Produce the `writing_task` artifact for the academic paper writing workflow stage `requirement_analysis`.

## Inputs
The Agent prepares a JSON input file containing upstream artifact content and task instructions.

Before preparing the input file, verify that the user's request includes enough information to create a writing task:
- topic or research area
- paper type and expected scope
- core argument or research focus
- any required style, language, citation, deadline, or institution constraints

If required information is missing, call `ask_user` with a concise question and a `missing_fields` list. Do not run this Skill script until the human response supplies enough information.

## Outputs
The script writes a JSON output file. The Agent then records it with `update_artifact_manifest` and advances the ProgressLedger with `update_progress`.

## Usage

```text
python skill_packs/academic-paper-writing/skills/writing-requirement-analysis/scripts/run.py --input path/to/input.json --output path/to/output.json
```

The script is deterministic and does not call an LLM.
