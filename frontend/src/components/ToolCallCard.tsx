import type { ToolCallSummary } from "./MessageBubble";

interface Props {
  toolCall: ToolCallSummary;
}

const toolIcons: Record<string, React.ReactNode> = {
  task: (
    <svg className="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" />
    </svg>
  ),
  execute_bash: (
    <svg className="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="4 17 10 11 4 5" />
      <line x1="12" y1="19" x2="20" y2="19" />
    </svg>
  ),
  ask_user: (
    <svg className="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  ),
};

const defaultIcon = (
  <svg className="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
    <line x1="3" y1="9" x2="21" y2="9" />
    <line x1="9" y1="21" x2="9" y2="9" />
  </svg>
);

const chevron = (
  <svg className="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="9 18 15 12 9 6" />
  </svg>
);

export function ToolCallCard({ toolCall }: Props) {
  const name = toolCall.name ?? "tool_call";
  return (
    <details className="tool-card">
      <summary>
        {toolIcons[name] ?? defaultIcon}
        {labelFor(name)}
        {chevron}
      </summary>
      <pre>{JSON.stringify(toolCall.args ?? {}, null, 2)}</pre>
    </details>
  );
}

function labelFor(name: string): string {
  const labels: Record<string, string> = {
    task: "子Agent 委派",
    execute_bash: "脚本执行",
    inspect_progress: "查看进度",
    update_progress: "更新进度",
    update_artifact_manifest: "更新产出清单",
    ask_user: "向用户提问",
    delegate_to_agent: "远程委派",
  };
  return labels[name] ?? name;
}
