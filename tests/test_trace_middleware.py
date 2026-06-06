from __future__ import annotations

from langchain_core.messages import ToolMessage

from middleware.trace import TraceMiddleware
from traces.store import TraceStore


class FakeToolRequest:
    def __init__(self) -> None:
        self.tool_call = {"id": "call-1", "name": "example_tool", "args": {"value": 123}}


def test_trace_middleware_records_successful_tool_call(tmp_path):
    trace_store = TraceStore(tmp_path / "trace.jsonl")
    middleware = TraceMiddleware(trace_store)

    result = middleware.wrap_tool_call(
        FakeToolRequest(),
        lambda request: {"status": "ok", "value": request.tool_call["args"]["value"]},
    )

    events = trace_store.read_all()
    assert result == {"status": "ok", "value": 123}
    assert len(events) == 1
    assert events[0].event_type == "tool_call"
    assert events[0].status == "success"
    assert events[0].payload == {
        "tool": "example_tool",
        "args": {"value": 123},
        "result": {"status": "ok", "value": 123},
    }


def test_trace_middleware_records_failed_tool_call(tmp_path):
    trace_store = TraceStore(tmp_path / "trace.jsonl")
    middleware = TraceMiddleware(trace_store)

    def handler(_request):
        raise ValueError("boom")

    result = middleware.wrap_tool_call(FakeToolRequest(), handler)

    events = trace_store.read_all()
    assert isinstance(result, ToolMessage)
    assert result.content == "Tool 'example_tool' failed: boom"
    assert result.tool_call_id == "call-1"
    assert len(events) == 1
    assert events[0].event_type == "tool_call"
    assert events[0].status == "failed"
    assert events[0].payload == {
        "tool": "example_tool",
        "args": {"value": 123},
        "error": "boom",
        "error_type": "ValueError",
    }
