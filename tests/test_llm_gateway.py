from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent.llm_gateway import LLMGateway
from agent.trace_store import TraceStore


def test_llm_gateway_structured_json_mock_records_trace(tmp_path: Path) -> None:
    trace_store = TraceStore(tmp_path)
    gateway = LLMGateway(trace_store=trace_store)

    payload = gateway.structured_json(
        caller="main_agent",
        system_prompt="Return JSON.",
        user_prompt="x",
        output_schema={"type": "object"},
        mock_payload={"ok": True},
    )

    assert payload == {"ok": True}
    lines = trace_store.llm_trace_path.read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0])["caller"] == "main_agent"


def test_llm_gateway_repairs_invalid_json_with_transport(tmp_path: Path) -> None:
    trace_store = TraceStore(tmp_path)
    gateway = LLMGateway(trace_store=trace_store, transport=SequenceTransport(["not json", '{"fixed": true}']))

    payload = gateway.structured_json(
        caller="main_agent",
        system_prompt="Return JSON.",
        user_prompt="x",
        output_schema={"type": "object"},
    )

    assert payload == {"fixed": True}


class SequenceTransport:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        return self.responses.pop(0)
