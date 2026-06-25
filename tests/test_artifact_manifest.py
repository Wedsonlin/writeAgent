from __future__ import annotations

import json

from artifacts.manifest import ArtifactManifest
from artifacts.schemas import ArtifactMeta


def test_manifest_add_depends_update_and_query(tmp_path):
    manifest = ArtifactManifest.load(tmp_path / "manifest.json")
    meta = manifest.upsert(ArtifactMeta(
        artifact_id="a1",
        artifact_type="outline",
        path="artifacts/outline.json",
        depends_on=["task1"],
        summary="old",
    ))
    assert meta.depends_on == ["task1"]

    updated = manifest.update_summary("a1", "new summary")
    assert updated.summary == "new summary"
    assert updated.version == 2
    assert manifest.list_by_type("outline")[0].artifact_id == "a1"


def test_manifest_upsert_merges_stale_instances(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    first = ArtifactManifest.load(manifest_path)
    second = ArtifactManifest.load(manifest_path)

    first.upsert(ArtifactMeta(
        artifact_id="writing_task",
        artifact_type="writing_task",
        path="artifacts/writing_task.json",
    ))
    second.upsert(ArtifactMeta(
        artifact_id="task_book_markdown",
        artifact_type="task_book_markdown",
        path="artifacts/writing_task.md",
        depends_on=["writing_task"],
    ))

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact_ids = {item["artifact_id"] for item in data["artifacts"]}
    assert artifact_ids == {"writing_task", "task_book_markdown"}


def test_manifest_load_recovers_legacy_trailing_garbage(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({
            "artifacts": [
                {
                    "artifact_id": "writing_task",
                    "artifact_type": "writing_task",
                    "path": "artifacts/writing_task.json",
                }
            ]
        })
        + '} stale tail',
        encoding="utf-8",
    )

    manifest = ArtifactManifest.load(manifest_path)

    assert manifest.get("writing_task") is not None
