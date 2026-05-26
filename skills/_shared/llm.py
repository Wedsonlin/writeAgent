"""OpenAI-compatible LLM client used by every Skill.

Why a shared file?
    * Each Skill *must* be a self-contained subprocess (OpenClaw rule).
    * But re-implementing the client in every Skill is wasteful.
    * Skills add ``skills/_shared`` to ``sys.path`` in their entry script and
      ``from _shared.llm import chat, structured_json``.

Configuration is fully via environment variables — works identically whether the
caller is OpenClaw's ReAct brain or the LangGraph orchestrator:

* ``WRITEAGENT_LLM_API_KEY``
* ``WRITEAGENT_LLM_BASE_URL``   (e.g. https://dashscope.aliyuncs.com/compatible-mode/v1)
* ``WRITEAGENT_LLM_MODEL``      (e.g. qwen-plus)
* ``WRITEAGENT_MOCK_LLM=1``     opt-in offline mock for tests / no-network CI
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
from dataclasses import dataclass
from typing import Any


__all__ = ["LLMConfig", "chat", "structured_json", "is_mock_mode"]


@dataclass
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    timeout: float = 90.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> "LLMConfig":
        api_key = os.environ.get("WRITEAGENT_LLM_API_KEY", "")
        base_url = os.environ.get(
            "WRITEAGENT_LLM_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        model = os.environ.get("WRITEAGENT_LLM_MODEL", "qwen-plus")
        return cls(api_key=api_key, base_url=base_url, model=model)


def is_mock_mode() -> bool:
    """Mock mode is active when explicitly requested or when no API key is set."""
    if os.environ.get("WRITEAGENT_MOCK_LLM") == "1":
        return True
    return not os.environ.get("WRITEAGENT_LLM_API_KEY")


def chat(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    response_format: dict[str, Any] | None = None,
    mock_response: str | None = None,
) -> str:
    """Synchronously call the chat completion endpoint.

    Returns the raw text content of the first choice. Caller is responsible for
    parsing JSON if ``response_format`` was requested.

    The ``mock_response`` argument lets the caller provide a deterministic stub
    when ``is_mock_mode()`` is true — typically a function-specific canned
    payload built from local heuristics.
    """
    if is_mock_mode():
        if mock_response is None:
            raise RuntimeError(
                "Mock mode is active but no mock_response was provided. "
                "Set WRITEAGENT_LLM_API_KEY or pass a stub to chat()."
            )
        return mock_response

    cfg = LLMConfig.from_env()
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "openai package is required. Run `pip install -r requirements-core.txt`."
        ) from exc

    client = OpenAI(api_key=cfg.api_key, base_url=cfg.base_url, timeout=cfg.timeout)

    last_err: Exception | None = None
    for attempt in range(cfg.max_retries):
        try:
            kwargs: dict[str, Any] = {
                "model": cfg.model,
                "messages": messages,
                "temperature": temperature,
            }
            if response_format is not None:
                kwargs["response_format"] = response_format
            completion = client.chat.completions.create(**kwargs)
            content = completion.choices[0].message.content or ""
            return content
        except Exception as exc:
            last_err = exc
            backoff = (2 ** attempt) + random.uniform(0, 0.5)
            print(
                f"[_shared.llm] attempt {attempt + 1}/{cfg.max_retries} failed: {exc}; "
                f"retry in {backoff:.1f}s",
                file=sys.stderr,
            )
            time.sleep(backoff)
    raise RuntimeError(f"LLM call failed after {cfg.max_retries} retries: {last_err}")


def structured_json(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.1,
    mock_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convenience wrapper that asks the model for a JSON object and parses it.

    Most OpenAI-compatible providers accept ``response_format={"type":"json_object"}``;
    if a provider refuses we still fall back to parsing the text body, tolerating
    stray ``` fences.
    """
    if is_mock_mode():
        if mock_payload is None:
            raise RuntimeError(
                "structured_json called in mock mode without a mock_payload."
            )
        return mock_payload

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    raw = chat(
        messages,
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    return _parse_json_lenient(raw)


def _parse_json_lenient(text: str) -> dict[str, Any]:
    """Tolerate ```json fences and surrounding chatter."""
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end > start:
            return json.loads(candidate[start : end + 1])
        raise
