import { useMemo, useState } from "react";

interface Props {
  interrupt: unknown;
  onResume: (resume: unknown) => void;
}

export function InterruptCard({ interrupt, onResume }: Props) {
  const request = useMemo(() => firstActionRequest(interrupt), [interrupt]);
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
              onResume({ decisions: [{ type: "respond", message: response }] });
            }}
          >
            <textarea
              value={response}
              onChange={(event) => setResponse(event.target.value)}
              placeholder="输入给 Agent 的回复…"
            />
            <button className="btn btn-approve" type="submit" disabled={!response.trim()}>
              提交回复
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
            <button className="btn btn-approve" type="button" onClick={() => onResume({ decisions: [{ type: "approve" }] })}>
              批准执行
            </button>
            <button className="btn btn-reject" type="button" onClick={() => onResume({ decisions: [{ type: "reject" }] })}>
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
                  })
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

function commandFrom(request: ActionRequest | null): string {
  const command = request?.args.command;
  return typeof command === "string" ? command : "";
}
