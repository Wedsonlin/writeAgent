from __future__ import annotations

from project_store.workspace import resolve_allowed_path


def test_resolve_allowed_path_maps_virtual_root_to_default(tmp_path):
    resolved = resolve_allowed_path("/", default=tmp_path, allowed_roots=[tmp_path])

    assert resolved == tmp_path.resolve()


def test_resolve_allowed_path_maps_virtual_absolute_path_under_default(tmp_path):
    resolved = resolve_allowed_path("/case/input.md", default=tmp_path, allowed_roots=[tmp_path])

    assert resolved == (tmp_path / "case" / "input.md").resolve()
