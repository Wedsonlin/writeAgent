"""Local delegation adapter."""

from __future__ import annotations

from typing import Any

from delegation.schema import DelegationRequest, DelegationResult


class LocalDelegationAdapter:
    backend = "local"

    def invoke(self, handle: Any, request: DelegationRequest) -> DelegationResult:
        if handle is None:
            return DelegationResult(status="blocked", summary="No local agent handle configured.")
        if callable(handle):
            raw = handle(request)
        elif hasattr(handle, "invoke"):
            raw = handle.invoke({"messages": [{"role": "user", "content": request.instruction}]})
        else:
            return DelegationResult(status="failed", summary="Unsupported local agent handle.")
        if isinstance(raw, DelegationResult):
            return raw
        if isinstance(raw, dict):
            return DelegationResult(status=raw.get("status", "ok"), summary=str(raw.get("summary", raw)))
        return DelegationResult(status="ok", summary=str(raw))
