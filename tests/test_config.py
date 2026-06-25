from __future__ import annotations

from agent_core.config import ModelConfig


def test_model_config_uses_openai_compatible_env(monkeypatch):
    monkeypatch.setenv("WRITEAGENT_MODEL", "openai:qwen-plus")
    monkeypatch.setenv("WRITEAGENT_LLM_API_KEY", "test-key")
    monkeypatch.setenv("WRITEAGENT_LLM_BASE_URL", "https://example.test/v1")

    config = ModelConfig.from_env()

    assert type(config.model).__name__ == "ChatOpenAI"
    assert getattr(config.model, "model_name") == "qwen-plus"
    assert str(getattr(config.model, "openai_api_base")) == "https://example.test/v1"
    assert getattr(config.model, "disable_streaming") is True
