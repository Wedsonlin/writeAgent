import assert from "node:assert/strict";
import { normalizeMessage } from "./messageNormalize.ts";

const serializedHuman = {
  lc: 1,
  type: "constructor",
  id: ["langchain_core", "messages", "HumanMessage"],
  kwargs: {
    content: "旧会话需求",
    type: "human",
    id: "human-1",
  },
};

const serializedAi = {
  lc: 1,
  type: "constructor",
  id: ["langchain_core", "messages", "AIMessage"],
  kwargs: {
    content: "已恢复旧会话",
    type: "ai",
    tool_calls: [
      {
        id: "call-1",
        name: "inspect_progress",
        args: {},
      },
    ],
  },
};

const serializedTool = {
  lc: 1,
  type: "constructor",
  id: ["langchain_core", "messages", "ToolMessage"],
  kwargs: {
    content: "{\"status\":\"ok\"}",
    type: "tool",
    name: "inspect_progress",
  },
};

assert.deepEqual(normalizeMessage(serializedHuman), {
  role: "human",
  content: "旧会话需求",
  name: undefined,
  parsed: undefined,
  toolCalls: [],
});

const ai = normalizeMessage(serializedAi);
assert.equal(ai.role, "ai");
assert.equal(ai.content, "已恢复旧会话");
assert.deepEqual(ai.toolCalls, [{ id: "call-1", name: "inspect_progress", args: {} }]);

const tool = normalizeMessage(serializedTool);
assert.equal(tool.role, "tool");
assert.equal(tool.name, "inspect_progress");
assert.deepEqual(tool.parsed, { status: "ok" });

console.log("messageNormalize tests passed");
