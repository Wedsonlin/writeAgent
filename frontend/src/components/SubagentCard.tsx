interface Props {
  subagent: Record<string, unknown>;
}

export function SubagentCard({ subagent }: Props) {
  const name = String(subagent.name ?? subagent.nodeName ?? "subagent");
  const status = String(subagent.status ?? "active");
  const description = String(subagent.description ?? subagent.task ?? "");
  const barClass = status === "completed" || status === "done"
    ? "completed"
    : status === "error" || status === "failed"
      ? "error"
      : "";
  const dotClass = status === "completed" || status === "done" ? "idle" : "running";

  return (
    <article className="subagent-card">
      <div className={`subagent-bar ${barClass}`} />
      <div className="subagent-body">
        <div className="subagent-card-header">
          <strong>{name}</strong>
          <span className="subagent-status">
            <span className={`status-dot ${dotClass}`} />
            {status}
          </span>
        </div>
        {description && <p>{description}</p>}
      </div>
    </article>
  );
}
