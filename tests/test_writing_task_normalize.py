from __future__ import annotations

import importlib.util
from pathlib import Path

from agent.subagents.factory import SubAgentFactory
from agent.subagents.schema_defaults import default_output_schema

ROOT = Path(__file__).resolve().parents[1]
NORMALIZE_PATH = ROOT / "skills" / "writing-requirement-analysis" / "scripts" / "normalize.py"


def _load_normalize():
    spec = importlib.util.spec_from_file_location("writing_task_normalize", NORMALIZE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_default_output_schema_for_requirement_key() -> None:
    assert default_output_schema("intermediate.requirement.raw_writing_task") == "WritingTask"


def test_factory_fills_missing_output_schema_from_output_key() -> None:
    spec = SubAgentFactory().from_action_input(
        {
            "role": "analyst",
            "task": "analyze",
            "input_keys": ["user_request"],
            "output_key": "intermediate.requirement.raw_writing_task",
        }
    )
    assert spec.output_schema == "WritingTask"


def test_normalize_markdown_payload() -> None:
    normalize = _load_normalize()
    payload = {
        "raw_writing_task": (
            "### 论文主题\n生成式AI辅助学术写作\n\n"
            "### 论文类型\n综述论文\n\n"
            "### 核心研究问题\n1. 应用模式是什么？\n2. 工具有哪些？\n\n"
            "#### 第一章 引言\n- 背景\n\n#### 第二章 文献综述\n- 回顾\n"
        )
    }
    normalized = normalize.normalize_writing_task_payload(payload)
    assert normalized["topic"] == "生成式AI辅助学术写作"
    assert normalized["paper_type"] == "survey"
    assert len(normalized["core_arguments"]) == 2
    assert len(normalized["chapter_framework"]) == 2
