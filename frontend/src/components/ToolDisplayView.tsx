import type { ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ToolDisplayModel, ToolDisplayTone } from "../lib/toolDisplay";

interface ToolDisplayViewProps {
  display: ToolDisplayModel;
  rawLabel: string;
}

export function ToolDisplayView({ display, rawLabel }: ToolDisplayViewProps) {
  const hasDetails =
    display.keyValues.length > 0 ||
    display.todos.length > 0 ||
    display.paths.length > 0 ||
    Boolean(display.markdown);

  return (
    <div className="tool-display-body">
      {display.summary && <p className="tool-display-summary">{display.summary}</p>}

      {display.keyValues.length > 0 && (
        <dl className="tool-field-grid">
          {display.keyValues.map((item) => (
            <div className="tool-field" key={`${item.label}-${item.value}`}>
              <dt>{item.label}</dt>
              <dd className={item.mono ? "mono" : undefined}>{item.value}</dd>
            </div>
          ))}
        </dl>
      )}

      {display.todos.length > 0 && (
        <ol className="tool-todo-list">
          {display.todos.map((todo, index) => (
            <li className={`tool-todo-item ${todo.tone}`} key={`${todo.content}-${index}`}>
              <span className="todo-check">{todo.tone === "success" ? "✓" : index + 1}</span>
              <span className="todo-content">{todo.content}</span>
              <span className={`todo-status ${todo.tone}`}>{todo.statusLabel}</span>
            </li>
          ))}
        </ol>
      )}

      {display.paths.length > 0 && (
        <div className="tool-path-list" aria-label="相关路径">
          {display.paths.map((path) => (
            <code key={path}>{path}</code>
          ))}
        </div>
      )}

      {display.markdown && (
        <div className="tool-markdown">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{display.markdown}</ReactMarkdown>
        </div>
      )}

      <details className={`tool-raw-details ${hasDetails ? "" : "only"}`}>
        <summary>{rawLabel}</summary>
        <pre>{display.rawText}</pre>
      </details>
    </div>
  );
}

export function ToolHeader({
  display,
  icon,
}: {
  display: ToolDisplayModel;
  icon: ReactNode;
}) {
  return (
    <>
      {icon}
      <span className="tool-heading">
        <span className="tool-title">{display.title}</span>
        {display.summary && <span className="tool-subtitle">{display.summary}</span>}
      </span>
      <ToolStatusBadge label={display.statusLabel} tone={display.statusTone} />
    </>
  );
}

export function ToolStatusBadge({ label, tone }: { label?: string; tone?: ToolDisplayTone }) {
  if (!label) {
    return null;
  }
  return <span className={`tool-status-badge ${tone ?? "neutral"}`}>{label}</span>;
}

export function ToolGlyph({ name }: { name: string }) {
  const icon = toolIcons[name] ?? defaultIcon;
  return icon;
}

const toolIcons: Record<string, ReactNode> = {
  ask_user: (
    <svg className="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  ),
  delegate_to_agent: (
    <svg className="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 3h5v5" />
      <path d="M8 21H3v-5" />
      <path d="M21 3l-7 7" />
      <path d="M3 21l7-7" />
    </svg>
  ),
  execute_bash: (
    <svg className="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="4 17 10 11 4 5" />
      <line x1="12" y1="19" x2="20" y2="19" />
    </svg>
  ),
  read_file: (
    <svg className="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  ),
  task: (
    <svg className="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" />
    </svg>
  ),
  update_progress: (
    <svg className="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12h4l3 8 4-16 3 8h4" />
    </svg>
  ),
  write_todos: (
    <svg className="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 11l3 3L22 4" />
      <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
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
