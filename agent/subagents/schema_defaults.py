"""Default output_schema names for common intermediate output keys."""

from __future__ import annotations

OUTPUT_KEY_SCHEMA_DEFAULTS: dict[str, str] = {
    "intermediate.requirement.raw_writing_task": "WritingTask",
    "intermediate.outline.raw_outline": "PaperOutline",
    "intermediate.literature_review.paper_claims": "PaperClaimsExtraction",
    "intermediate.literature_review.synthesis": "LiteratureSynthesis",
}


def default_output_schema(output_key: str) -> str | None:
    return OUTPUT_KEY_SCHEMA_DEFAULTS.get(output_key)


__all__ = ["OUTPUT_KEY_SCHEMA_DEFAULTS", "default_output_schema"]
