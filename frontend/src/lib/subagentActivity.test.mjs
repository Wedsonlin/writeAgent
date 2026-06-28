import assert from "node:assert/strict";
import {
  latestSubagentActivityItem,
  subagentChildIdsFromToolCalls,
} from "./subagentActivity.ts";

const latest = latestSubagentActivityItem(
  [
    {
      type: "ai",
      content: "我会先拆解论文任务，再检索相关证据。",
    },
    {
      type: "tool",
      name: "search_knowledge",
      content: JSON.stringify({
        query: "agent writing",
        results: [{ title: "secret result" }],
      }),
    },
    {
      role: "assistant",
      content: [{ type: "text", text: "根据检索结果整理章节计划。" }],
    },
  ],
  [
    {
      name: "extract_sources",
      args: { urls: ["https://example.com/private-paper"] },
    },
    {
      toolName: "execute_bash",
      input: { command: "python secret.py --token abc" },
    },
  ],
);

assert.deepEqual(latest, {
  id: "tool-execute_bash-1",
  kind: "tool",
  label: "正在执行 execute_bash",
});

const rendered = latest.label;
assert.ok(!rendered.includes("agent writing"));
assert.ok(!rendered.includes("secret result"));
assert.ok(!rendered.includes("private-paper"));
assert.ok(!rendered.includes("token abc"));

assert.deepEqual(latestSubagentActivityItem([], []), {
  id: "waiting",
  kind: "thinking",
  label: "等待子 Agent 开始输出",
});

assert.deepEqual(
  subagentChildIdsFromToolCalls([
    { id: "call_child_a", name: "task", args: { subagent_type: "paper-outline-agent" } },
    { id: "call_child_b", name: "delegate_to_agent", args: { receiver_agent_id: "literature-agent" } },
    { id: "call_ignored", name: "execute_bash", args: { command: "secret" } },
  ]),
  ["call_child_a", "call_child_b"],
);

console.log("subagentActivity tests passed");
