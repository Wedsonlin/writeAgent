"""Remote A2A adapter wrapper.

This adapter intentionally does not implement a wire protocol. It delegates to an
injected official A2A-compatible client object in production and is mockable in tests.
"""

from __future__ import annotations

from typing import Any

from delegation.schema import DelegationRequest, DelegationResult


class RemoteA2AAdapter:
    backend = "remote_a2a"

    def __init__(self, client: Any | None = None) -> None:
        self.client = client

    def invoke(self, handle: Any, request: DelegationRequest) -> DelegationResult:
        client = handle or self.client
        if client is None:
            return DelegationResult(status="blocked", summary="No official A2A client configured.")
        raw = client.send(request.model_dump()) if hasattr(client, "send") else client(request.model_dump())
        if isinstance(raw, DelegationResult):
            return raw
        if isinstance(raw, dict):
            return DelegationResult.model_validate(raw)
        return DelegationResult(status="failed", summary="Remote A2A client returned an unsupported response.")
