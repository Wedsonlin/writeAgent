"""Minimal HTTP client for remote A2A-compatible delegation."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


class A2AHttpClient:
    """POST a delegation payload to an A2A-compatible endpoint."""

    def __init__(self, endpoint: str, *, timeout_sec: int = 30, headers: dict[str, str] | None = None) -> None:
        self.endpoint = endpoint
        self.timeout_sec = timeout_sec
        self.headers = {"Content-Type": "application/json", **(headers or {})}

    def send(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = Request(self.endpoint, data=body, headers=self.headers, method="POST")
        try:
            with urlopen(request, timeout=self.timeout_sec) as response:  # noqa: S310 - endpoint is explicit config
                response_body = response.read().decode("utf-8")
        except URLError as exc:
            return {
                "status": "failed",
                "summary": f"Remote A2A request failed: {exc.reason}",
                "output_artifacts": [],
                "messages": [],
            }
        return json.loads(response_body)
