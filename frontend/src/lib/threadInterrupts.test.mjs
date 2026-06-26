import assert from "node:assert/strict";
import {
  extractPendingInterrupts,
  extractThreadStreamInterrupts,
  mergeInterrupts,
  threadStateUrl,
} from "./threadInterrupts.ts";

const rootInterrupt = {
  id: "root-1",
  value: {
    action_requests: [{ name: "ask_user", args: { question: "root question" } }],
  },
};

const taskInterrupt = {
  id: "task-1",
  value: {
    action_requests: [{ name: "ask_user", args: { question: "task question" } }],
  },
};

const namespacedInterrupt = {
  id: "task-2",
  namespace: ["tools:real-tool-call", "agent:requirement-analysis-agent"],
  value: {
    action_requests: [{ name: "ask_user", args: { question: "namespaced question" } }],
  },
};

const state = {
  interrupts: {
    root_node: [rootInterrupt],
  },
  tasks: [
    {
      id: "task-node-1",
      name: "tools",
      interrupts: [taskInterrupt, rootInterrupt, namespacedInterrupt],
    },
  ],
};

const pending = extractPendingInterrupts(state);
assert.equal(pending.length, 3);
assert.equal(pending[0].id, "root-1");
assert.equal(pending[1].id, "task-1");
assert.equal(pending[1].namespace, undefined);
assert.deepEqual(pending[2].namespace, ["tools:real-tool-call", "agent:requirement-analysis-agent"]);

const threadMapState = {
  interrupts: {
    "79f1a8a2-fda6-ac89-9ea0-a176e66e9691": [taskInterrupt],
  },
};
const threadMapPending = extractPendingInterrupts(threadMapState);
assert.equal(threadMapPending.length, 1);
assert.equal(threadMapPending[0].namespace, undefined);

const streamThreadPending = extractThreadStreamInterrupts({
  interrupts: [
    {
      interruptId: "stream-sub-1",
      namespace: ["tools:real-tool-call", "agent:requirement-analysis-agent"],
      payload: {
        action_requests: [{ name: "ask_user", args: { question: "stream question" } }],
      },
    },
  ],
});
assert.equal(streamThreadPending.length, 1);
assert.equal(streamThreadPending[0].id, "stream-sub-1");
assert.equal(streamThreadPending[0].interruptId, "stream-sub-1");
assert.deepEqual(streamThreadPending[0].namespace, ["tools:real-tool-call", "agent:requirement-analysis-agent"]);
assert.deepEqual(streamThreadPending[0].value, {
  action_requests: [{ name: "ask_user", args: { question: "stream question" } }],
});

assert.deepEqual(mergeInterrupts([rootInterrupt], pending).map((item) => item.id), ["root-1", "task-1", "task-2"]);
assert.deepEqual(mergeInterrupts([], pending).map((item) => item.id), ["root-1", "task-1", "task-2"]);

assert.equal(
  threadStateUrl("http://localhost:2024", "e2b7170f-6971-4135-ae3f-900082e50a0c"),
  "http://localhost:2024/threads/e2b7170f-6971-4135-ae3f-900082e50a0c/state",
);

console.log("threadInterrupts tests passed");
