export interface ToolCallSummary {
  id?: string;
  name?: string;
  args?: unknown;
}

export function normalizeMessage(message: unknown): {
  role: string;
  content: string;
  name?: string;
  parsed?: unknown;
  toolCalls: ToolCallSummary[];
} {
  if (!message || typeof message !== "object") {
    return { role: "unknown", content: String(message ?? ""), toolCalls: [] };
  }
  const value = unwrapSerializedMessage(message as Record<string, unknown>);
  const getType = typeof value._getType === "function" ? value._getType : undefined;
  const role = String(value.role ?? value.type ?? getType?.call(value) ?? "message");
  const content = contentToText(value.content);
  return {
    role,
    content,
    name: typeof value.name === "string" ? value.name : undefined,
    parsed: parseJson(content),
    toolCalls: normalizeToolCalls(value.tool_calls ?? value.toolCalls),
  };
}

function unwrapSerializedMessage(value: Record<string, unknown>): Record<string, unknown> {
  if (value.type !== "constructor" || !value.kwargs || typeof value.kwargs !== "object") {
    return value;
  }
  const kwargs = value.kwargs as Record<string, unknown>;
  const role = stringValue(kwargs.type) ?? stringValue(kwargs.role) ?? roleFromConstructorId(value.id);
  return {
    ...kwargs,
    role: role ?? kwargs.role,
    type: role ?? kwargs.type,
  };
}

function roleFromConstructorId(raw: unknown): string | undefined {
  if (!Array.isArray(raw)) {
    return undefined;
  }
  const name = String(raw[raw.length - 1] ?? "");
  if (name === "HumanMessage") {
    return "human";
  }
  if (name === "AIMessage") {
    return "ai";
  }
  if (name === "ToolMessage") {
    return "tool";
  }
  if (name === "SystemMessage") {
    return "system";
  }
  return undefined;
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

function parseJson(content: string): unknown | undefined {
  try {
    return JSON.parse(content);
  } catch {
    return undefined;
  }
}

function stringValue(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}
