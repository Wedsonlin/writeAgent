import assert from "node:assert/strict";
import { messagesForDisplay } from "./sessionMessages.ts";

const persisted = [{ type: "human", content: "历史消息" }];
const live = [{ type: "ai", content: "实时消息" }];

assert.deepEqual(messagesForDisplay([], persisted), persisted);
assert.deepEqual(messagesForDisplay(live, persisted), live);

console.log("sessionMessages tests passed");
