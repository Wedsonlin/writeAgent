"""Async Tavily API client with per-event-loop connection pooling."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

import httpx


DEFAULT_TAVILY_BASE_URL = "https://api.tavily.com"


@dataclass(frozen=True)
class TavilySettings:
    api_key: str | None
    base_url: str = DEFAULT_TAVILY_BASE_URL
    timeout_sec: float = 30.0
    max_connections: int = 20
    max_keepalive_connections: int = 10

    @classmethod
    def from_env(cls) -> "TavilySettings":
        return cls(
            api_key=os.getenv("TAVILY_API_KEY"),
            base_url=os.getenv("TAVILY_BASE_URL", DEFAULT_TAVILY_BASE_URL).rstrip("/"),
            timeout_sec=float(os.getenv("WRITEAGENT_SEARCH_TIMEOUT_SEC", "30")),
            max_connections=int(os.getenv("WRITEAGENT_SEARCH_MAX_CONNECTIONS", "20")),
            max_keepalive_connections=int(os.getenv("WRITEAGENT_SEARCH_MAX_KEEPALIVE", "10")),
        )


class TavilyClient:
    """Small async Tavily REST client.

    `httpx.AsyncClient` is bound to the active event loop, so this class keeps a
    pooled client per loop. That supports connection reuse inside LangGraph's
    async runtime without breaking tests that use repeated `asyncio.run()`.
    """

    def __init__(self, settings: TavilySettings | None = None) -> None:
        self.settings = settings or TavilySettings.from_env()
        self._clients: dict[int, httpx.AsyncClient] = {}

    @property
    def api_key(self) -> str | None:
        return self.settings.api_key

    @property
    def is_available(self) -> bool:
        return bool(self.settings.api_key)

    async def search(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/search", payload)

    async def extract(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post("/extract", payload)

    async def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.api_key:
            raise RuntimeError("TAVILY_API_KEY is not configured")
        response = await self._client().post(
            endpoint,
            json=payload,
            headers={"Authorization": f"Bearer {self.settings.api_key}"},
        )
        response.raise_for_status()
        return response.json()

    def _client(self) -> httpx.AsyncClient:
        loop = asyncio.get_running_loop()
        key = id(loop)
        client = self._clients.get(key)
        if client is not None and not client.is_closed:
            return client

        limits = httpx.Limits(
            max_connections=self.settings.max_connections,
            max_keepalive_connections=self.settings.max_keepalive_connections,
        )
        timeout = httpx.Timeout(self.settings.timeout_sec)
        client = httpx.AsyncClient(
            base_url=self.settings.base_url,
            timeout=timeout,
            limits=limits,
            follow_redirects=True,
        )
        self._clients[key] = client
        return client


_SHARED_CLIENT: TavilyClient | None = None


def get_tavily_client() -> TavilyClient:
    global _SHARED_CLIENT
    if _SHARED_CLIENT is None:
        _SHARED_CLIENT = TavilyClient()
    return _SHARED_CLIENT
