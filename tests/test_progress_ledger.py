from __future__ import annotations

from project_store.ledger import ProgressLedger


def test_progress_ledger_create_update_and_next_stage(tmp_path):
    ledger = ProgressLedger.create("wf", ["requirement_analysis", "literature_review"])
    assert ledger.current_stage == "requirement_analysis"
    ledger.update_stage("requirement_analysis", "completed", output_artifacts=["writing_task"])
    assert ledger.current_stage == "literature_review"
    assert ledger.completed_stages() == ["requirement_analysis"]
    ledger.save(tmp_path / "progress.json")
    loaded = ProgressLedger.load(tmp_path / "progress.json")
    assert loaded.next_recommended_stage() == "literature_review"
