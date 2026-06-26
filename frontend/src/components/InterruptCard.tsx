import { useMemo, useState } from "react";

interface Props {
  interrupt: unknown;
  onResume: (resume: unknown, target?: ResumeTarget) => void;
  isSubmitting?: boolean;
  error?: string | null;
}

export function InterruptCard({ interrupt, onResume, isSubmitting = false, error = null }: Props) {
  const request = useMemo(() => firstActionRequest(interrupt), [interrupt]);
  const resumeTarget = useMemo(() => interruptTarget(interrupt), [interrupt]);
  const askUserPrompt = useMemo(() => askUserPromptFrom(request), [request]);
  const [response, setResponse] = useState("");
  const [editedCommand, setEditedCommand] = useState(() => commandFrom(request));
  const toolName = request?.name ?? "interrupt";

  return (
    <section className="interrupt-card">
      <div className="interrupt-bar" />
      <div className="interrupt-body">
        <div className="interrupt-header">
          <svg className="warn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          <div>
            <h3>需要人工确认</h3>
            <p className="interrupt-header">{toolName === "ask_user" ? "Agent 需要您补充信息后才能继续。" : "请审核即将执行的操作。"}</p>
          </div>
        </div>

        {toolName === "ask_user" && askUserPrompt && (
          <div className="interrupt-question-panel" aria-label="需要您回答的问题">
            <div className="interrupt-question-label">请回答</div>
            <p className="interrupt-question-text">{askUserPrompt.question}</p>
            {askUserPrompt.missingFields.length > 0 && (
              <div className="interrupt-question-section">
                <span>待确认信息</span>
                <ul className="interrupt-chip-list">
                  {askUserPrompt.missingFields.map((field) => (
                    <li key={field}>{field}</li>
                  ))}
                </ul>
              </div>
            )}
            {askUserPrompt.currentSummary && (
              <div className="interrupt-question-section">
                <span>当前已知信息</span>
                <p>{askUserPrompt.currentSummary}</p>
              </div>
            )}
          </div>
        )}

        <details className="tool-card">
          <summary>
            <svg className="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="16 18 22 12 16 6" />
              <polyline points="8 6 2 12 8 18" />
            </svg>
            查看原始数据
            <svg className="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </summary>
          <pre>{JSON.stringify(interrupt, null, 2)}</pre>
        </details>

        {toolName === "ask_user" ? (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              if (isSubmitting) {
                return;
              }
              onResume({ decisions: [{ type: "respond", message: response }] }, resumeTarget);
            }}
          >
            <textarea
              value={response}
              onChange={(event) => setResponse(event.target.value)}
              placeholder="输入给 Agent 的回复…"
            />
            {error ? <p className="input-error">{error}</p> : null}
            <button className="btn btn-approve" type="submit" disabled={isSubmitting || !response.trim()}>
              {isSubmitting ? "提交中..." : "提交回复"}
            </button>
          </form>
        ) : (
          <div className="interrupt-actions">
            {editedCommand && (
              <label>
                编辑命令
                <textarea value={editedCommand} onChange={(event) => setEditedCommand(event.target.value)} />
              </label>
            )}
            <button className="btn btn-approve" type="button" onClick={() => onResume({ decisions: [{ type: "approve" }] }, resumeTarget)}>
              批准执行
            </button>
            <button className="btn btn-reject" type="button" onClick={() => onResume({ decisions: [{ type: "reject" }] }, resumeTarget)}>
              拒绝
            </button>
            {editedCommand && request && (
              <button
                className="btn btn-edit"
                type="button"
                onClick={() =>
                  onResume({
                    decisions: [
                      {
                        type: "edit",
                        edited_action: {
                          name: request.name,
                          args: { ...request.args, command: editedCommand },
                        },
                      },
                    ],
                  }, resumeTarget)
                }
              >
                编辑后执行
              </button>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

interface ActionRequest {
  name: string;
  args: Record<string, unknown>;
}

interface AskUserPrompt {
  question: string;
  missingFields: string[];
  currentSummary?: string;
}

export interface ResumeTarget {
  interruptId?: string;
  namespace?: string[];
}

function firstActionRequest(interrupt: unknown): ActionRequest | null {
  const value = unwrapInterrupt(interrupt);
  const actionRequests = value?.action_requests;
  if (!Array.isArray(actionRequests) || !actionRequests[0]) {
    return null;
  }
  const request = actionRequests[0] as Record<string, unknown>;
  return {
    name: String(request.name ?? "interrupt"),
    args: (request.args && typeof request.args === "object" ? request.args : {}) as Record<string, unknown>,
  };
}

function unwrapInterrupt(interrupt: unknown): Record<string, unknown> | null {
  if (!interrupt || typeof interrupt !== "object") {
    return null;
  }
  const value = interrupt as Record<string, unknown>;
  if ("value" in value && value.value && typeof value.value === "object") {
    return value.value as Record<string, unknown>;
  }
  if (Array.isArray(value.__interrupt__) && value.__interrupt__[0]?.value) {
    return value.__interrupt__[0].value as Record<string, unknown>;
  }
  return value;
}

function interruptTarget(interrupt: unknown): ResumeTarget | undefined {
  if (!interrupt || typeof interrupt !== "object") {
    return undefined;
  }
  const value = interrupt as Record<string, unknown>;
  const interruptId = stringValue(value.id) ?? stringValue(value.interruptId) ?? stringValue(value.interrupt_id);
  const namespace = Array.isArray(value.namespace) ? value.namespace.map(String) : undefined;
  if (!interruptId) {
    return undefined;
  }
  return namespace && namespace.length > 0 ? { interruptId, namespace } : { interruptId };
}

function stringValue(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function stringListValue(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => String(item).trim()).filter(Boolean);
}

function askUserPromptFrom(request: ActionRequest | null): AskUserPrompt | null {
  if (!request || request.name !== "ask_user") {
    return null;
  }
  const question = stringValue(request.args.question)?.trim();
  if (!question) {
    return null;
  }
  return {
    question,
    missingFields: stringListValue(request.args.missing_fields),
    currentSummary: stringValue(request.args.current_summary)?.trim(),
  };
}

function commandFrom(request: ActionRequest | null): string {
  const command = request?.args.command;
  return typeof command === "string" ? command : "";
}
