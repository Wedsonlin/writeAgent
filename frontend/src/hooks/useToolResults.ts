import { useMemo } from "react";

export function useToolResults(messages: unknown[]) {
  return useMemo(() => {
    return messages
      .map((message) => normalizeToolMessage(message))
      .filter((item): item is ToolResult => item !== null);
  }, [messages]);
}

export interface ToolResult {
  id?: string;
  name?: string;
  content: string;
  parsed?: unknown;
}

function normalizeToolMessage(message: unknown): ToolResult | null {
  if (!message || typeof message !== "object") {
    return null;
  }
  const value = message as Record<string, unknown>;
  const role = value.role ?? value.type;
  if (role !== "tool") {
    return null;
  }
  const content = stringifyContent(value.content);
  return {
    id: typeof value.tool_call_id === "string" ? value.tool_call_id : undefined,
    name: typeof value.name === "string" ? value.name : undefined,
    content,
    parsed: parseJson(content),
  };
}

function stringifyContent(content: unknown): string {
  if (typeof content === "string") {
    return content;
  }
  return JSON.stringify(content, null, 2);
}

function parseJson(content: string): unknown | undefined {
  try {
    return JSON.parse(content);
  } catch {
    return undefined;
  }
}
