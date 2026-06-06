from __future__ import annotations

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
