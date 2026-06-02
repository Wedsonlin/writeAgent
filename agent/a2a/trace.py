"""Small helpers for A2A trace serialization."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .types import SubAgentTrace


def trace_to_dict(trace: SubAgentTrace) -> dict[str, Any]:
    return asdict(trace)


__all__ = ["trace_to_dict"]
