"""Governed LLM access for Main Agent and dynamic Sub-agents."""

from __future__ import annotations

import json
import os
import random
import time
import uuid
from dataclasses import dataclass
from typing import Any

from .trace_store import TraceStore, now_iso


@dataclass
class LLMGatewayConfig:
    api_key: str
    base_url: str
    model: str
    timeout: float = 90.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> "LLMGatewayConfig":
        return cls(
            api_key=os.environ.get("WRITEAGENT_LLM_API_KEY", ""),
            base_url=os.environ.get(
                "WRITEAGENT_LLM_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
            model=os.environ.get("WRITEAGENT_LLM_MODEL", "qwen-plus"),
        )


class LLMGateway:
    """Single model-call surface for all Agent-native reasoning."""

    def __init__(
        self,
        *,
        config: LLMGatewayConfig | None = None,
        trace_store: TraceStore | None = None,
        transport: Any | None = None,
    ) -> None:
        self.config = config or LLMGatewayConfig.from_env()
        self.trace_store = trace_store
        self.transport = transport

    def is_mock_mode(self) -> bool:
        return os.environ.get("WRITEAGENT_MOCK_LLM") == "1" or not self.config.api_key

    def chat(
        self,
        *,
        caller: str,
        messages: list[dict[str, str]],
        call_type: str = "chat",
        model_policy: dict[str, Any] | None = None,
        temperature: float | None = None,
        response_format: dict[str, Any] | None = None,
        mock_response: str | None = None,
    ) -> str:
        call_id = _call_id()
        started = time.perf_counter()
        policy = dict(model_policy or {})
        model = str(policy.get("model") or self.config.model)
        temp = float(policy.get("temperature", temperature if temperature is not None else 0.2))
        try:
            if self.transport is not None:
                raw = self._call_transport(messages, temperature=temp, response_format=response_format, mock_response=mock_response)
            elif self.is_mock_mode():
                if mock_response is None:
                    raise RuntimeError("LLMGateway mock mode requires mock_response.")
                raw = mock_response
            else:
                raw = self._call_openai(messages, model=model, temperature=temp, response_format=response_format)
            self._record_call(
                call_id=call_id,
                caller=caller,
                call_type=call_type,
                status="ok",
                started=started,
                model=model,
                messages=messages,
                response=raw,
            )
            return raw
        except Exception as exc:
            self._record_call(
                call_id=call_id,
                caller=caller,
                call_type=call_type,
                status="error",
                started=started,
                model=model,
                messages=messages,
                error=str(exc),
            )
            raise

    def structured_json(
        self,
        *,
        caller: str,
        system_prompt: str,
        user_prompt: str,
        output_schema: str | dict[str, Any] | None = None,
        call_type: str = "structured_json",
        model_policy: dict[str, Any] | None = None,
        temperature: float | None = None,
        mock_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.is_mock_mode() and self.transport is None:
            if mock_payload is None:
                raise RuntimeError("LLMGateway structured_json mock mode requires mock_payload.")
            self._record_call(
                call_id=_call_id(),
                caller=caller,
                call_type=call_type,
                status="ok",
                started=time.perf_counter(),
                model=str((model_policy or {}).get("model") or self.config.model),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response=json.dumps(mock_payload, ensure_ascii=False),
            )
            return mock_payload
        raw = self.chat(
            caller=caller,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            call_type=call_type,
            model_policy=model_policy,
            temperature=temperature,
            response_format={"type": "json_object"},
            mock_response=json.dumps(mock_payload, ensure_ascii=False) if mock_payload is not None else None,
        )
        try:
            return parse_json_lenient(raw)
        except json.JSONDecodeError:
            repaired = self.repair_json(caller=caller, raw_output=raw, output_schema=output_schema, model_policy=model_policy)
            return parse_json_lenient(repaired)

    def repair_json(
        self,
        *,
        caller: str,
        raw_output: str,
        output_schema: str | dict[str, Any] | None = None,
        model_policy: dict[str, Any] | None = None,
    ) -> str:
        schema_text = json.dumps(output_schema, ensure_ascii=False) if output_schema is not None else "No schema provided."
        return self.chat(
            caller=caller,
            messages=[
                {"role": "system", "content": "Return only a valid JSON object. No Markdown."},
                {
                    "role": "user",
                    "content": (
                        "Repair this invalid JSON output.\n"
                        f"Schema:\n{schema_text}\n\n"
                        f"Raw output:\n{raw_output}"
                    ),
                },
            ],
            call_type="json_repair",
            model_policy=model_policy,
            temperature=0.0,
            response_format={"type": "json_object"},
            mock_response=raw_output,
        )

    def _call_transport(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        if hasattr(self.transport, "chat"):
            return str(self.transport.chat(messages, **kwargs))
        return str(self.transport(messages, **kwargs))

    def _call_openai(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        temperature: float,
        response_format: dict[str, Any] | None,
    ) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is required for LLMGateway.") from exc

        client = OpenAI(api_key=self.config.api_key, base_url=self.config.base_url, timeout=self.config.timeout)
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries):
            try:
                kwargs: dict[str, Any] = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                }
                if response_format is not None:
                    kwargs["response_format"] = response_format
                completion = client.chat.completions.create(**kwargs)
                return completion.choices[0].message.content or ""
            except Exception as exc:
                last_error = exc
                if attempt + 1 >= self.config.max_retries:
                    break
                time.sleep((2**attempt) + random.uniform(0, 0.5))
        raise RuntimeError(f"LLM call failed after {self.config.max_retries} retries: {last_error}")

    def _record_call(
        self,
        *,
        call_id: str,
        caller: str,
        call_type: str,
        status: str,
        started: float,
        model: str,
        messages: list[dict[str, str]],
        response: str = "",
        error: str | None = None,
    ) -> None:
        if self.trace_store is None:
            return
        self.trace_store.append_llm_trace(
            {
                "call_id": call_id,
                "caller": caller,
                "call_type": call_type,
                "status": status,
                "model": model,
                "started_at": now_iso(),
                "duration_ms": int((time.perf_counter() - started) * 1000),
                "usage": {
                    "prompt_chars": sum(len(m.get("content", "")) for m in messages),
                    "completion_chars": len(response),
                },
                "error": error,
            }
        )


def parse_json_lenient(text: str) -> dict[str, Any]:
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()
    try:
        loaded = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end <= start:
            raise
        loaded = json.loads(candidate[start : end + 1])
    if not isinstance(loaded, dict):
        raise json.JSONDecodeError("Expected JSON object", candidate, 0)
    return loaded


def _call_id() -> str:
    return "llm_" + uuid.uuid4().hex[:12]


__all__ = ["LLMGateway", "LLMGatewayConfig", "parse_json_lenient"]
