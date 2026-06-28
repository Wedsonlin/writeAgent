import { useMemo } from "react";
import { useMessages, useToolCalls, type UseStreamReturn } from "@langchain/react";
import { latestSubagentActivityItem, subagentChildIdsFromToolCalls } from "../lib/subagentActivity";

interface Props {
  stream: UseStreamReturn<Record<string, unknown>, unknown, Record<string, unknown>>;
  subagent: Record<string, unknown>;
  subagentsById: Map<string, Record<string, unknown>>;
  ancestorIds?: string[];
  depth?: number;
}

const maxSubagentDepth = 6;

export function SubagentCard({ stream, subagent, subagentsById, ancestorIds = [], depth = 0 }: Props) {
  const name = String(subagent.name ?? subagent.nodeName ?? "subagent");
  const subagentId = String(subagent.id ?? "");
  const rawStatus = String(subagent.status ?? "active");
  const errorMessage = typeof subagent.error === "string" ? subagent.error : "";
  const description = String(subagent.description ?? subagent.task ?? subagent.taskInput ?? "");
  const scopedMessages = useMessages(stream as never, subagent as never) as unknown[];
  const scopedToolCalls = useToolCalls(stream as never, subagent as never) as unknown[];
  const currentActivity = useMemo(
    () => latestSubagentActivityItem(scopedMessages, scopedToolCalls),
    [scopedMessages, scopedToolCalls],
  );
  const childSubagents = useMemo(() => {
    if (depth >= maxSubagentDepth) {
      return [];
    }
    const blockedIds = new Set([...ancestorIds, subagentId].filter(Boolean));
    return subagentChildIdsFromToolCalls(scopedToolCalls)
      .filter((id) => !blockedIds.has(id))
      .map((id) => subagentsById.get(id))
      .filter((item): item is Record<string, unknown> => Boolean(item));
  }, [ancestorIds, depth, scopedToolCalls, subagentId, subagentsById]);
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
    <div className="subagent-card-stack">
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
          <div className={`subagent-activity ${currentActivity.kind}`} aria-label={`${name} current activity`}>
            <span className="subagent-activity-dot" />
            <span>{currentActivity.label}</span>
          </div>
          {errorMessage && status.key === "error" && <p className="subagent-error">{errorMessage}</p>}
        </div>
      </article>
      {childSubagents.length > 0 ? (
        <div className="subagent-children">
          {childSubagents.map((child, index) => (
            <SubagentCard
              key={String(child.id ?? index)}
              stream={stream}
              subagent={child}
              subagentsById={subagentsById}
              ancestorIds={[...ancestorIds, subagentId].filter(Boolean)}
              depth={depth + 1}
            />
          ))}
        </div>
      ) : null}
    </div>
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
