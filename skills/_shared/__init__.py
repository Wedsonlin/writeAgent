"""Shared utilities for OpenClaw-compatible Skills.

This package is intentionally light-weight and dependency-free of LangGraph/LangChain
so that any Skill can run inside the OpenClaw runtime via plain ``python run.py``.

Modules
-------
- :mod:`._shared.io`       Read/write the shared ``state.json`` workspace artifact.
- :mod:`._shared.schemas`  Pydantic models mirroring ``schemas/*.schema.json``.
"""
