from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ContractError(Exception):
    message: str
    fields: list[str]

    def __str__(self) -> str:
        return self.message


def validate_report_input(data: dict[str, Any]) -> None:
    missing: list[str] = []
    if not isinstance(data.get("writing_task"), dict):
        missing.append("writing_task")
    if not isinstance(data.get("source_map"), list):
        missing.append("source_map")
    if not isinstance(data.get("landscape"), dict):
        missing.append("landscape")
    if missing:
        raise ContractError("literature review input is missing critical fields", missing)


def validate_report(report: dict[str, Any], core_argument_count: int) -> None:
    paper_ids = {paper["id"] for paper in report.get("papers", []) if isinstance(paper, dict) and paper.get("id")}
    invalid_cluster_ids: list[str] = []
    for cluster in report.get("research_landscape", {}).get("clusters", []):
        for paper_id in cluster.get("paper_ids", []):
            if paper_id not in paper_ids:
                invalid_cluster_ids.append(str(paper_id))

    invalid_alignments: list[str] = []
    for paper in report.get("papers", []):
        for item in paper.get("alignment_to_core", []):
            index = item.get("core_argument_index")
            if not isinstance(index, int) or index < 0 or index >= core_argument_count:
                invalid_alignments.append(f"{paper.get('id')}:{index}")

    fields: list[str] = []
    if invalid_cluster_ids:
        fields.append(f"landscape.clusters.paper_ids={invalid_cluster_ids}")
    if invalid_alignments:
        fields.append(f"source_map.alignment_to_core={invalid_alignments}")
    if fields:
        raise ContractError("literature review output failed consistency checks", fields)
