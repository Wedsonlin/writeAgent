"""LangGraph dev server graph entrypoint."""

from __future__ import annotations

from agent_core.config import RuntimeConfig
from agent_core.factory import create_write_agent


_cfg = RuntimeConfig()
_cfg.ensure_dirs()

graph = create_write_agent(_cfg, checkpointer=None)
