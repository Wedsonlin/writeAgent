import assert from "node:assert/strict";
import {
  artifactRootForProject,
  createProjectSession,
  loadProjectSession,
  normalizeThreadId,
  projectSessionFromApi,
  projectQuery,
  sessionDisplayLabel,
  shouldActivateProjectSession,
  sortProjectSessions,
} from "./projectSession.ts";
import { artifactFileUrl, workflowProgressUrl } from "../api/workflow.ts";

const uuid = "8f3a1234-1111-4222-8333-abcdefabcdef";
const session = createProjectSession({
  now: new Date(2026, 5, 26, 14, 30, 12),
  randomUUID: () => uuid,
});

assert.equal(session.threadId, uuid);
assert.equal(session.projectName, `20260626-143012_thread-${uuid}`);
assert.equal(
  artifactRootForProject(session.projectName),
  `.writeagent/projects/20260626-143012_thread-${uuid}/artifacts`,
);
assert.equal(projectQuery(session.projectName), `project_id=20260626-143012_thread-${uuid}`);
assert.equal(
  workflowProgressUrl(session.projectName),
  `http://localhost:2024/api/workflow/progress?project_id=20260626-143012_thread-${uuid}`,
);
assert.equal(
  artifactFileUrl("formatted-1", "docx", session.projectName),
  `http://localhost:2024/api/artifacts/formatted-1/files/docx?project_id=20260626-143012_thread-${uuid}`,
);

const legacyStorage = memoryStorage();
legacyStorage.setItem("writeagent_project_session", JSON.stringify({
  threadId: `thread-${uuid}`,
  projectName: `20260626-143012_thread-${uuid}`,
  createdAt: "2026-06-26T06:30:12.000Z",
}));
const migrated = loadProjectSession(legacyStorage);
assert.equal(migrated?.threadId, uuid);
assert.equal(migrated?.projectName, `20260626-143012_thread-${uuid}`);

const projectNameThreadStorage = memoryStorage();
projectNameThreadStorage.setItem("writeagent_project_session", JSON.stringify({
  threadId: `20260626-143012_thread-${uuid}`,
  projectName: `20260626-143012_thread-${uuid}`,
  createdAt: "2026-06-26T06:30:12.000Z",
}));
const migratedProjectNameThread = loadProjectSession(projectNameThreadStorage);
assert.equal(migratedProjectNameThread?.threadId, uuid);
assert.equal(migratedProjectNameThread?.projectName, `20260626-143012_thread-${uuid}`);
assert.equal(normalizeThreadId(`20260626-143012_thread-${uuid}`), uuid);

const restored = projectSessionFromApi({
  project_id: `20260626-143012_thread-${uuid}`,
  thread_id: uuid,
  created_at: "2026-06-26T06:30:12.000Z",
  updated_at: "2026-06-27T05:00:00.000Z",
  root: `C:\\repo\\.writeagent\\projects\\20260626-143012_thread-${uuid}`,
});
assert.equal(restored?.threadId, uuid);
assert.equal(restored?.projectName, `20260626-143012_thread-${uuid}`);
assert.equal(restored?.updatedAt, "2026-06-27T05:00:00.000Z");

const older = {
  ...restored,
  projectName: "20260625-110000_thread-9f3a1234-1111-4222-8333-abcdefabcdef",
  threadId: "9f3a1234-1111-4222-8333-abcdefabcdef",
  createdAt: "2026-06-25T03:00:00.000Z",
  updatedAt: "2026-06-25T04:00:00.000Z",
};
assert.deepEqual(
  sortProjectSessions([older, restored]).map((item) => item.projectName),
  [`20260626-143012_thread-${uuid}`, "20260625-110000_thread-9f3a1234-1111-4222-8333-abcdefabcdef"],
);

assert.equal(
  sessionDisplayLabel({
    threadId: "ab45b623-fc0c-495d-b579-d3884e0dab8b",
    projectName: "20260626-100222_thread-ab45b623-fc0c-495d-b579-d3884e0dab8b",
    createdAt: "2026-06-26T10:02:22.000Z",
  }),
  "2026-06-26 10:02 · ab45b623",
);

assert.equal(shouldActivateProjectSession({}), false);
assert.equal(shouldActivateProjectSession({ liveMessageCount: 0, persistedMessageCount: 0, isRunning: false, knownSession: false }), false);
assert.equal(shouldActivateProjectSession({ liveMessageCount: 1 }), true);
assert.equal(shouldActivateProjectSession({ persistedMessageCount: 1 }), true);
assert.equal(shouldActivateProjectSession({ isRunning: true }), true);
assert.equal(shouldActivateProjectSession({ knownSession: true }), true);

const invalidStorage = memoryStorage();
invalidStorage.setItem("writeagent_project_session", JSON.stringify({
  threadId: "thread-8f3a1234",
  projectName: "20260626-143012_thread-8f3a1234",
  createdAt: "2026-06-26T06:30:12.000Z",
}));
assert.equal(loadProjectSession(invalidStorage), null);

console.log("projectSession tests passed");

function memoryStorage() {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: (key) => values.delete(key),
  };
}
