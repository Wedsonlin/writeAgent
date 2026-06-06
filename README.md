# writeAgent

writeAgent is now a Deep Agents based academic paper writing agent. Deep Agents owns the general harness: planning, todo management, filesystem, context compression, skills disclosure, local subagents, memory, checkpointer, middleware composition, and human review.

writeAgent owns the paper-writing domain layer: the academic Skill Pack, workflow gate, ArtifactManifest, ProgressLedger, A2A-compatible delegation facade, controlled bash execution, trace records, and writing quality controls.

## Runtime

```powershell
python -m pip install -r requirements-orchestrator.txt
writeagent "????? AI ??????????????"
```

The local CLI invokes `agent_core.runtime.WriteAgentRuntime`. There is no deployment server in this repository.

## Directory Map

```text
agent_core/        Deep Agents factory, context, config, local runtime
middleware/        workflow gate, trace, guardrails, human review policy
tools/             execute_bash, progress, artifact manifest, delegation tools
delegation/        local and remote A2A-compatible delegation facade
workflows/         workflow loading, gate decisions, progress helpers
artifacts/         ArtifactManifest and artifact schemas
project_store/     project metadata, ProgressLedger, checkpointer adapter
traces/            local JSONL trace store
skill_packs/       academic-paper-writing Skill Pack
```

Skills are readable and executable directories inside the Skill Pack. Scripts are deterministic and are invoked through `execute_bash` with file input/output arguments.
