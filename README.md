# writeAgent

writeAgent is now a Deep Agents based academic paper writing agent. Deep Agents owns the general harness: planning, todo management, filesystem, context compression, skills disclosure, local subagents, memory, checkpointer, middleware composition, and human review.

writeAgent owns the paper-writing domain layer: the academic Skill Pack, workflow gate, ArtifactManifest, ProgressLedger, A2A-compatible delegation facade, controlled bash execution, trace records, and writing quality controls.

## Runtime

```powershell
python -m pip install -r requirements-orchestrator.txt
writeagent "????? AI ??????????????"
```

The local CLI invokes `agent_core.runtime.WriteAgentRuntime`.

## Frontend Development

Phase 1 includes a local LangGraph API server plus a React/Vite frontend for monitoring the Deep Agents workflow.

Install Python dependencies in the `writeagent` environment:

```powershell
conda run -n writeagent python -m pip install -r requirements-orchestrator.txt
```

Create `.env` from `.env.example` and fill the writeAgent model settings:

```env
WRITEAGENT_LLM_API_KEY=sk-your-deepseek-key
WRITEAGENT_LLM_BASE_URL=https://api.deepseek.com
WRITEAGENT_MODEL=openai:deepseek-v4-flash
```

The `openai:` model prefix selects the OpenAI-compatible LangChain adapter; it does not mean the request must go to OpenAI. For DeepSeek, use `deepseek-v4-flash` by default, or `deepseek-v4-pro` when higher quality matters more than latency or cost. Keep real API keys in `.env` only and do not commit them.

Start the LangGraph development server from the repository root:

```powershell
conda activate writeagent
set PYTHONUTF8=1
langgraph dev --config langgraph.json --no-browser --no-reload
```

Use `--no-reload` to avoid noisy `changes detected` logs from `.langgraph_api` persistence flushes during local development.

In a second terminal, start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. If Vite reports port 5173 is in use, stop the other process on that port first (the frontend is configured with `strictPort: true` so it will not silently switch ports). The UI connects to `http://localhost:2024` with `assistantId=writeagent`, renders coordinator messages, subagent cards, HITL interrupt cards, tool calls, and the six-stage workflow progress bar.

## Directory Map

```text
agent_core/        Deep Agents factory, context, config, local runtime
server/            LangGraph graph entrypoint and custom workflow REST routes
frontend/          React/Vite frontend using @langchain/react useStream
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
