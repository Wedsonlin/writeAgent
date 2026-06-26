import assert from "node:assert/strict";
import {
  artifactRootForProject,
  createProjectSession,
  loadProjectSession,
  normalizeThreadId,
  projectQuery,
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
