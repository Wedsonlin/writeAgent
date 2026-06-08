import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ToolCallCard } from "./ToolCallCard";

interface Props {
  message: unknown;
}

const roleIcons: Record<string, { label: string; icon: React.ReactNode }> = {
  human: {
    label: "用户",
    icon: (
      <svg className="role-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 19.5c0-2.5-3.6-4.5-8-4.5s-8 2-8 4.5" />
        <circle cx="12" cy="8" r="4" />
      </svg>
    ),
  },
  user: {
    label: "用户",
    icon: (
      <svg className="role-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 19.5c0-2.5-3.6-4.5-8-4.5s-8 2-8 4.5" />
        <circle cx="12" cy="8" r="4" />
      </svg>
    ),
  },
  ai: {
    label: "Agent",
    icon: (
      <svg className="role-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
        <path d="M8 7h6" />
        <path d="M8 11h4" />
      </svg>
    ),
  },
  assistant: {
    label: "Agent",
    icon: (
      <svg className="role-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
        <path d="M8 7h6" />
        <path d="M8 11h4" />
      </svg>
    ),
  },
  tool: {
    label: "工具",
    icon: (
      <svg className="role-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </svg>
    ),
  },
};

export function MessageBubble({ message }: Props) {
  const normalized = normalizeMessage(message);
  if (!normalized.content && normalized.toolCalls.length === 0) {
    return null;
  }

  const roleInfo = roleIcons[normalized.role];

  return (
    <div className={`message ${normalized.role}`}>
      <div className="message-role">
        {roleInfo?.icon}
        {roleInfo?.label ?? normalized.role}
      </div>
      {normalized.content && (
        <div className="message-content">
          {normalized.role === "ai" || normalized.role === "assistant" ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{normalized.content}</ReactMarkdown>
          ) : (
            normalized.content
          )}
        </div>
      )}
      {normalized.toolCalls.length > 0 && (
        <div className="tool-call-list">
          {normalized.toolCalls.map((toolCall, index) => (
            <ToolCallCard key={toolCall.id ?? index} toolCall={toolCall} />
          ))}
        </div>
      )}
    </div>
  );
}

export interface ToolCallSummary {
  id?: string;
  name?: string;
  args?: unknown;
}

export function normalizeMessage(message: unknown): {
  role: string;
  content: string;
  toolCalls: ToolCallSummary[];
} {
  if (!message || typeof message !== "object") {
    return { role: "unknown", content: String(message ?? ""), toolCalls: [] };
  }
  const value = message as Record<string, unknown>;
  const getType = typeof value._getType === "function" ? value._getType : undefined;
  const role = String(value.role ?? value.type ?? getType?.call(value) ?? "message");
  return {
    role,
    content: contentToText(value.content),
    toolCalls: normalizeToolCalls(value.tool_calls ?? value.toolCalls),
  };
}

function normalizeToolCalls(raw: unknown): ToolCallSummary[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
    .map((item) => ({
      id: typeof item.id === "string" ? item.id : undefined,
      name: typeof item.name === "string" ? item.name : undefined,
      args: item.args,
    }));
}

function contentToText(content: unknown): string {
  if (typeof content === "string") {
    return content;
  }
  if (Array.isArray(content)) {
    return content
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }
        if (item && typeof item === "object" && "text" in item) {
          return String((item as { text: unknown }).text);
        }
        return "";
      })
      .filter(Boolean)
      .join("\n");
  }
  return content == null ? "" : JSON.stringify(content, null, 2);
}
