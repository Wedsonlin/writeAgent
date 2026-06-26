import { FormEvent, useMemo, useState } from "react";
import { useStream } from "@langchain/react";
import { agentUrl, fetchCaseRequirement } from "./api/workflow";
import { ChatPanel } from "./components/ChatPanel";
import { InterruptCard, type ResumeTarget } from "./components/InterruptCard";
import { WorkflowProgress } from "./components/WorkflowProgress";
import { type ToolResult, useToolResults } from "./hooks/useToolResults";
import { useWorkflowProgress } from "./hooks/useWorkflowProgress";
import {
  artifactRootForProject,
  createProjectSession,
  ensureProjectSession,
  normalizeThreadId,
  projectNameForThread,
  projectRootForProject,
  saveProjectSession,
  type ProjectSession,
} from "./lib/projectSession";
import type { WorkflowMeta, WorkflowProgressPayload } from "./types/workflow";
import "./styles.css";

export default function App() {
  const [input, setInput] = useState("");
  const [caseLoadError, setCaseLoadError] = useState<string | null>(null);
  const [isLoadingCase, setIsLoadingCase] = useState(false);
  const [projectSession, setProjectSession] = useState<ProjectSession>(() => ensureProjectSession());
  const stream = useStream({
    apiUrl: agentUrl,
    assistantId: "writeagent",
    fetchStateHistory: true,
    reconnectOnMount: true,
    onThreadId: (id: string) => {
      const normalizedThreadId = normalizeThreadId(id);
      if (!normalizedThreadId) {
        return;
      }
      setProjectSession((current) => {
        if (current.threadId === normalizedThreadId) {
          return current;
        }
        const timestamp = current.projectName.split("_")[0] || current.projectName;
        const next = { ...current, threadId: normalizedThreadId, projectName: projectNameForThread(timestamp, normalizedThreadId) };
        saveProjectSession(next);
        return next;
      });
    },
    threadId: normalizeThreadId(projectSession.threadId) ?? undefined,
  } as never);
  const messages = stream.messages ?? [];
  const subagents = useMemo(
    () => Array.from((stream.subagents ?? new Map()).values()) as unknown as Record<string, unknown>[],
    [stream.subagents],
  );
  const streamInterrupts = (stream as { interrupts?: unknown[] }).interrupts ?? [];
  const activeInterrupt = stream.interrupt ?? streamInterrupts[0];
  const isRunning = Boolean(stream.isLoading);
  const workflow = useWorkflowProgress(isRunning, projectSession.projectName);
  const toolResults = useToolResults(messages);
  const streamError = stringifyError(stream.error);
  const displayedProgress = useMemo(
    () => deriveProgressFromTools(workflow.meta, workflow.progress, toolResults, projectSession.projectName),
    [workflow.meta, workflow.progress, toolResults, projectSession.projectName],
  );

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text) {
      return;
    }
    setInput("");
    void stream.submit(
      { messages: [{ role: "human", content: text }] },
      {
        config: { configurable: runtimeContext(projectSession) },
        metadata: { source: "frontend" },
        onError: (error: unknown) => console.error("writeAgent stream error", error),
      } as never,
    );
  }

  function handleNewSession() {
    const next = createProjectSession();
    saveProjectSession(next);
    setProjectSession(next);
    window.location.reload();
  }

  async function handleLoadCaseRequirement() {
    setCaseLoadError(null);
    setIsLoadingCase(true);
    try {
      const payload = await fetchCaseRequirement();
      setInput(payload.content);
    } catch (error) {
      setCaseLoadError(stringifyError(error) ?? "无法载入 case 原始需求");
    } finally {
      setIsLoadingCase(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="header-brand">
          <svg className="header-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
            <path d="M8 7h6" />
            <path d="M8 11h4" />
          </svg>
          <div>
            <h1>writeAgent</h1>
            <p>学术论文写作工作流监控平台</p>
          </div>
        </div>
        <div className="header-actions">
          <button className="header-link header-button" type="button" onClick={handleNewSession}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12a9 9 0 1 1-2.64-6.36" />
              <polyline points="21 3 21 9 15 9" />
            </svg>
            新建会话
          </button>
          <a className="header-link" href={agentUrl} target="_blank" rel="noreferrer">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
            LangGraph API
          </a>
        </div>
      </header>

      <WorkflowProgress
        meta={workflow.meta}
        progress={displayedProgress}
        error={workflow.error ?? streamError}
        projectId={projectSession.projectName}
      />

      <section className="status-strip">
        <span className="status-item">
          <span className={`status-dot ${isRunning ? "running" : "idle"}`} />
          {isRunning ? "运行中" : "空闲"}
        </span>
        <span className="status-item">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" />
          </svg>
          子 Agent：{subagents.length}
        </span>
        <span className="status-item">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <line x1="3" y1="9" x2="21" y2="9" />
            <line x1="9" y1="21" x2="9" y2="9" />
          </svg>
          工具结果：{toolResults.length}
        </span>
      </section>

      <ChatPanel messages={messages} subagents={subagents} />

      {activeInterrupt ? (
        <InterruptCard
          interrupt={activeInterrupt}
          onResume={(resume, target) =>
            void stream
              .respond(resume, respondOptions(projectSession, target) as never)
              .catch((error: unknown) => console.error("writeAgent resume error", error))
          }
        />
      ) : null}

      <form className="chat-input" onSubmit={handleSubmit}>
        <div className="input-stack">
          <button className="prompt-chip" type="button" onClick={handleLoadCaseRequirement} disabled={isLoadingCase}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="8" y1="13" x2="16" y2="13" />
              <line x1="8" y1="17" x2="13" y2="17" />
            </svg>
            {isLoadingCase ? "载入中" : "载入 case 需求"}
          </button>
          {caseLoadError ? <span className="input-error">{caseLoadError}</span> : null}
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            rows={2}
            placeholder="输入指令，例如：请根据 case/00 开始需求分析…"
            onKeyDown={(event) => {
              if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
                event.currentTarget.form?.requestSubmit();
              }
            }}
          />
        </div>
        <button className="send-btn" type="submit" disabled={isRunning || !input.trim()}>
          发送
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </form>
    </main>
  );
}

function runtimeContext(projectSession: ProjectSession) {
  const projectRoot = projectRootForProject(projectSession.projectName);
  return {
    user_id: "frontend-user",
    workspace_id: "local",
    project_id: projectSession.projectName,
    skill_pack_id: "academic-paper-writing",
    project_root: projectRoot,
    artifact_root: artifactRootForProject(projectSession.projectName),
    tmp_root: `${projectRoot}/tmp`,
    evidence_root: `${projectRoot}/evidence`,
    cache_root: `${projectRoot}/cache`,
    locale: "zh-CN",
    citation_style: "GB/T 7714",
  };
}

function respondOptions(projectSession: ProjectSession, target?: ResumeTarget) {
  return {
    ...target,
    config: { configurable: runtimeContext(projectSession) },
    metadata: { source: "frontend" },
  };
}

function stringifyError(error: unknown): string | null {
  if (!error) {
    return null;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

function deriveProgressFromTools(
  meta: WorkflowMeta | null,
  base: WorkflowProgressPayload | null,
  toolResults: ToolResult[],
  expectedProjectId?: string | null,
): WorkflowProgressPayload | null {
  let current = base;
  for (const result of toolResults) {
    if (!result.parsed || typeof result.parsed !== "object") {
      continue;
    }
    const parsed = result.parsed as Record<string, unknown>;
    if (!isProgressForCurrentProject(parsed, expectedProjectId)) {
      continue;
    }
    if (Array.isArray(parsed.completed_stages) || Array.isArray(parsed.pending_stages)) {
      current = fromInspectProgress(meta, current, parsed, expectedProjectId);
    } else if (parsed.stage && typeof parsed.stage === "object") {
      current = fromUpdateProgress(current, parsed);
    }
  }
  return current;
}

function fromInspectProgress(
  meta: WorkflowMeta | null,
  base: WorkflowProgressPayload | null,
  parsed: Record<string, unknown>,
  expectedProjectId?: string | null,
): WorkflowProgressPayload | null {
  if (!meta) {
    return base;
  }
  const completed = new Set((parsed.completed_stages as unknown[] | undefined)?.map(String) ?? []);
  const pending = new Set((parsed.pending_stages as unknown[] | undefined)?.map(String) ?? []);
  const currentStage = typeof parsed.current_stage === "string" ? parsed.current_stage : base?.current_stage ?? null;
  return {
    workflow_id: base?.workflow_id ?? meta.workflow_id,
    project_id: (typeof parsed.project_id === "string" ? parsed.project_id : null) ?? base?.project_id ?? expectedProjectId ?? undefined,
    current_stage: currentStage,
    blocked_reason: (parsed.blocked_reason as string | null | undefined) ?? base?.blocked_reason ?? null,
    updated_at: base?.updated_at ?? new Date().toISOString(),
    artifacts: Array.isArray(parsed.artifacts) ? (parsed.artifacts as WorkflowProgressPayload["artifacts"]) : base?.artifacts ?? [],
    stages: meta.stages.map((stage) => ({
      stage_id: stage.id,
      status: completed.has(stage.id)
        ? "completed"
        : stage.id === currentStage
          ? "in_progress"
          : pending.has(stage.id)
            ? "pending"
            : base?.stages.find((item) => item.stage_id === stage.id)?.status ?? "pending",
      input_artifacts: base?.stages.find((item) => item.stage_id === stage.id)?.input_artifacts ?? [],
      output_artifacts: base?.stages.find((item) => item.stage_id === stage.id)?.output_artifacts ?? [],
      blocked_reason: null,
      updated_at: base?.updated_at ?? new Date().toISOString(),
    })),
  };
}

function isProgressForCurrentProject(parsed: Record<string, unknown>, expectedProjectId?: string | null): boolean {
  if (!expectedProjectId) {
    return true;
  }
  const projectId = parsed.project_id;
  return typeof projectId !== "string" || projectId === expectedProjectId;
}

function fromUpdateProgress(base: WorkflowProgressPayload | null, parsed: Record<string, unknown>): WorkflowProgressPayload | null {
  if (!base) {
    return null;
  }
  const stage = parsed.stage as Record<string, unknown>;
  const stageId = String(stage.stage_id ?? "");
  if (!stageId) {
    return base;
  }
  return {
    ...base,
    current_stage: typeof parsed.current_stage === "string" ? parsed.current_stage : base.current_stage,
    stages: base.stages.map((item) => (item.stage_id === stageId ? { ...item, ...stage } as WorkflowProgressPayload["stages"][number] : item)),
  };
}
