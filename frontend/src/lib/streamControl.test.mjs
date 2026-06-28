import assert from "node:assert/strict";

import { shouldShowTerminateGeneration, terminateGeneration } from "./streamControl.ts";

assert.equal(shouldShowTerminateGeneration({ isRunning: false, isTerminating: false }), false);
assert.equal(shouldShowTerminateGeneration({ isRunning: true, isTerminating: false }), true);
assert.equal(shouldShowTerminateGeneration({ isRunning: false, isTerminating: true }), true);

const calls = [];
await terminateGeneration({
  stop(options) {
    calls.push(options);
  },
});
assert.deepEqual(calls, [{ cancel: true }]);

await assert.rejects(
  () => terminateGeneration({}),
  /does not support termination/,
);

console.log("streamControl tests passed");
