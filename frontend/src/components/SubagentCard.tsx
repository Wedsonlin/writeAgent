interface Props {
  subagent: Record<string, unknown>;
}

export function SubagentCard({ subagent }: Props) {
  const name = String(subagent.name ?? subagent.nodeName ?? "subagent");
  const rawStatus = String(subagent.status ?? "active");
  const errorMessage = typeof subagent.error === "string" ? subagent.error : "";
  const description = String(subagent.description ?? subagent.task ?? subagent.taskInput ?? "");
  const status = formatSubagentStatus(rawStatus, errorMessage);
  const barClass = status.key === "completed"
    ? "completed"
    : status.key === "error"
      ? "error"
      : status.key === "awaiting"
        ? "awaiting"
        : "";
  const dotClass = status.key === "completed" ? "idle" : status.key === "error" ? "idle" : "running";

  return (
    <article className="subagent-card">
      <div className={`subagent-bar ${barClass}`} />
      <div className="subagent-body">
        <div className="subagent-card-header">
          <strong>{name}</strong>
          <span className="subagent-status">
            <span className={`status-dot ${dotClass}`} />
            {status.label}
          </span>
        </div>
        {description && <p>{description}</p>}
        {errorMessage && status.key === "error" && <p className="subagent-error">{errorMessage}</p>}
      </div>
    </article>
  );
}

function formatSubagentStatus(rawStatus: string, errorMessage: string): { key: string; label: string } {
  if (rawStatus === "completed" || rawStatus === "complete" || rawStatus === "done") {
    return { key: "completed", label: "completed" };
  }
  if (rawStatus === "error" || rawStatus === "failed") {
    if (/ask_user|approval|interrupt|requires approval/i.test(errorMessage)) {
      return { key: "awaiting", label: "awaiting input" };
    }
    return { key: "error", label: "error" };
  }
  if (rawStatus === "pending") {
    return { key: "pending", label: "pending" };
  }
  return { key: "running", label: rawStatus || "running" };
}
