"""Schema helpers for local A2A structured outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = REPO_ROOT / "schemas"

NAMED_SCHEMA_FILES = {
    "WritingTask": "writing_task.schema.json",
    "raw_writing_task_schema": "writing_task.schema.json",
    "PaperOutline": "paper_outline.schema.json",
    "PaperClaimsExtraction": "paper_claims.schema.json",
    "LiteratureSynthesis": "literature_synthesis.schema.json",
    "LiteratureReport": "literature_report.schema.json",
    "PaperOutline": "paper_outline.schema.json",
    "PaperDraft": "paper_draft.schema.json",
    "FormatReport": "format_report.schema.json",
    "PolishReport": "polish_report.schema.json",
}


def load_output_schema(schema_ref: str | dict[str, Any] | None) -> dict[str, Any] | None:
    """Load an inline or named JSON schema.

    Unknown named schemas return a permissive object schema. This keeps the A2A
    protocol stable while allowing new intermediate schemas to be introduced by
    prompt name before a formal JSON schema file exists.
    """
    if schema_ref is None:
        return None
    if isinstance(schema_ref, dict):
        return schema_ref
    filename = NAMED_SCHEMA_FILES.get(schema_ref)
    if not filename:
        return {"type": "object"}
    path = SCHEMAS_DIR / filename
    if not path.exists():
        return {"type": "object"}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {"type": "object"}


def validate_json_schema(value: Any, schema: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Validate only the lightweight subset of JSON Schema used by tests.

    The project already uses Pydantic inside deterministic Skill scripts for
    formal artifacts. Sub-agents validate intermediate shape here without adding
    another heavy dependency.
    """
    if schema is None:
        return []
    errors: list[dict[str, Any]] = []
    _validate(value, schema, "$", errors)
    return errors


def _validate(value: Any, schema: dict[str, Any], path: str, errors: list[dict[str, Any]]) -> None:
    expected_type = schema.get("type")
    if isinstance(expected_type, list):
        if not any(_matches_type(value, t) for t in expected_type):
            errors.append({"code": "schema_type", "path": path, "message": f"Expected one of {expected_type}."})
            return
    elif isinstance(expected_type, str) and not _matches_type(value, expected_type):
        errors.append({"code": "schema_type", "path": path, "message": f"Expected {expected_type}."})
        return

    if isinstance(value, dict):
        required = schema.get("required") or []
        if isinstance(required, list):
            for key in required:
                if key not in value:
                    errors.append({"code": "schema_required", "path": f"{path}.{key}", "message": "Missing required field."})
        properties = schema.get("properties") or {}
        if isinstance(properties, dict):
            for key, child_schema in properties.items():
                if key in value and isinstance(child_schema, dict):
                    _validate(value[key], child_schema, f"{path}.{key}", errors)
    elif isinstance(value, list):
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                _validate(item, item_schema, f"{path}[{index}]", errors)


def _matches_type(value: Any, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "null":
        return value is None
    return True


__all__ = ["NAMED_SCHEMA_FILES", "load_output_schema", "validate_json_schema"]
