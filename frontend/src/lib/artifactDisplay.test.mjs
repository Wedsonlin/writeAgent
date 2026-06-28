import assert from "node:assert/strict";

import {
  isArtifactPathInArtifactRoot,
  visibleArtifactsInArtifactRoot,
} from "./artifactDisplay.ts";

const projectId = "20260627-143023_thread-demo";

const artifacts = [
  {
    artifact_id: "task-json",
    path: `.writeagent/projects/${projectId}/artifacts/01-task.json`,
  },
  {
    artifact_id: "absolute-docx",
    path: `C:/repo/.writeagent/projects/${projectId}/artifacts/final.docx`,
  },
  {
    artifact_id: "relative-markdown",
    path: "artifacts/03-draft.md",
  },
  {
    artifact_id: "cache-entry",
    path: `.writeagent/projects/${projectId}/cache/search.json`,
  },
  {
    artifact_id: "evidence-entry",
    path: `/.writeagent/projects/${projectId}/evidence/source.md`,
  },
  {
    artifact_id: "tmp-entry",
    path: `.writeagent/projects/${projectId}/tmp/input.json`,
  },
  {
    artifact_id: "other-project-artifact",
    path: ".writeagent/projects/other-project/artifacts/foreign.json",
  },
  {
    artifact_id: "missing-path",
  },
];

assert.deepEqual(
  visibleArtifactsInArtifactRoot(artifacts, projectId).map((artifact) => artifact.artifact_id),
  ["task-json", "absolute-docx", "relative-markdown"],
);

assert.equal(
  isArtifactPathInArtifactRoot(`/.writeagent/projects/${projectId}/artifacts/a.json`, projectId),
  true,
);
assert.equal(
  isArtifactPathInArtifactRoot(`.writeagent\\projects\\${projectId}\\artifacts\\a.json`, projectId),
  true,
);
assert.equal(
  isArtifactPathInArtifactRoot(`/.writeagent/projects/${projectId}/cache/a.json`, projectId),
  false,
);
assert.equal(
  isArtifactPathInArtifactRoot("/.writeagent/projects/other-project/artifacts/a.json", projectId),
  false,
);
assert.equal(isArtifactPathInArtifactRoot("/.writeagent/projects/other-project/artifacts/a.json"), true);
