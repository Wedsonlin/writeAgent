export type SubagentActivityKind = "thinking" | "tool";

export interface SubagentActivityItem {
  id: string;
  kind: SubagentActivityKind;
  label: string;
}

const maxActivityItems = 12;
const maxThoughtLength = 96;
const subagentToolNames = new Set(["task", "delegate_to_agent"]);

export function latestSubagentActivityItem(messages: unknown[], toolCalls: unknown[]): SubagentActivityItem {
  const items = buildSubagentActivityItems(messages, toolCalls);
  return items[items.length - 1] ?? waitingActivity();
}

export function subagentChildIdsFromToolCalls(toolCalls: unknown[]): string[] {
  return toolCalls
    .filter((toolCall) => {
      const toolName = toolNameFromCall(toolCall);
      return Boolean(toolName && subagentToolNames.has(toolName));
    })
    .map((toolCall) => toolIdFromCall(toolCall))
    .filter((id): id is string => Boolean(id));
}

export function buildSubagentActivityItems(messages: unknown[], toolCalls: unknown[]): SubagentActivityItem[] {
  const items: SubagentActivityItem[] = [];
  const seenTools = new Set<string>();

  for (const [index, message] of messages.entries()) {
    const normalized = normalizeMessage(message);
    if (normalized.role === "tool" || normalized.role === "function") {
      const toolName = normalized.name;
      const toolId = normalized.toolCallId ?? normalized.id ?? `${toolName}-${index}`;
      if (toolName && !seenTools.has(toolId)) {
        seenTools.add(toolId);
        items.push(toolActivity(toolId, toolName));
      }
      continue;
    }

    if (normalized.content) {
      items.push({
        id: `message-${normalized.id ?? index}`,
        kind: "thinking",
        label: `正在思考：${truncate(normalized.content)}`,
      });
    }

    for (const toolCall of normalized.toolCalls) {
      const toolName = toolNameFromCall(toolCall);
      const toolId = toolIdFromCall(toolCall) ?? `${toolName}-${index}`;
      if (!toolName || seenTools.has(toolId)) {
        continue;
      }
      seenTools.add(toolId);
      items.push(toolActivity(toolId, toolName));
    }
  }

  for (const [index, toolCall] of toolCalls.entries()) {
    const toolName = toolNameFromCall(toolCall);
    const toolId = toolIdFromCall(toolCall) ?? `${toolName}-${index}`;
    if (!toolName || seenTools.has(toolId)) {
      continue;
    }
    seenTools.add(toolId);
    items.push(toolActivity(toolId, toolName));
  }

  const visibleItems = items.slice(-maxActivityItems);
  return visibleItems.length > 0
    ? visibleItems
    : [waitingActivity()];
}

function normalizeMessage(message: unknown): {
  id?: string;
  name?: string;
  role: string;
  content: string;
  toolCallId?: string;
  toolCalls: unknown[];
} {
  if (!message || typeof message !== "object") {
    return { role: "unknown", content: contentToText(message), toolCalls: [] };
  }
  const value = message as Record<string, unknown>;
  const getType = typeof value._getType === "function" ? value._getType : undefined;
  return {
    id: stringValue(value.id),
    name: stringValue(value.name),
    role: String(value.role ?? value.type ?? getType?.call(value) ?? "message"),
    content: contentToText(value.content),
    toolCallId: stringValue(value.tool_call_id) ?? stringValue(value.toolCallId),
    toolCalls: arrayValue(value.tool_calls) ?? arrayValue(value.toolCalls) ?? [],
  };
}

function toolActivity(toolId: string, toolName: string): SubagentActivityItem {
  return {
    id: `tool-${toolId}`,
    kind: "tool",
    label: `正在执行 ${toolName}`,
  };
}

function waitingActivity(): SubagentActivityItem {
  return { id: "waiting", kind: "thinking", label: "等待子 Agent 开始输出" };
}

function toolNameFromCall(toolCall: unknown): string | null {
  if (!toolCall || typeof toolCall !== "object") {
    return null;
  }
  const value = toolCall as Record<string, unknown>;
  const nestedFunction = recordValue(value.function);
  return (
    stringValue(value.name) ??
    stringValue(value.toolName) ??
    stringValue(value.tool_name) ??
    stringValue(nestedFunction?.name) ??
    null
  );
}

function toolIdFromCall(toolCall: unknown): string | null {
  if (!toolCall || typeof toolCall !== "object") {
    return null;
  }
  const value = toolCall as Record<string, unknown>;
  return stringValue(value.id) ?? stringValue(value.tool_call_id) ?? stringValue(value.toolCallId) ?? null;
}

function contentToText(content: unknown): string {
  if (typeof content === "string") {
    return content.trim();
  }
  if (Array.isArray(content)) {
    return content
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }
        if (item && typeof item === "object") {
          const value = item as Record<string, unknown>;
          return stringValue(value.text) ?? stringValue(value.content) ?? "";
        }
        return "";
      })
      .filter(Boolean)
      .join("\n")
      .trim();
  }
  return "";
}

function truncate(value: string): string {
  const normalized = value.replace(/\s+/g, " ").trim();
  return normalized.length > maxThoughtLength
    ? `${normalized.slice(0, maxThoughtLength - 1)}…`
    : normalized;
}

function stringValue(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function arrayValue(value: unknown): unknown[] | undefined {
  return Array.isArray(value) ? value : undefined;
}

function recordValue(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}
