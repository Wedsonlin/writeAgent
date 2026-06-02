"""Print local LangChain ReAct acceptance scenarios for manual validation."""

from __future__ import annotations


SCENARIOS = [
    (
        "outline_only",
        "我只需要一份关于 EMI 技术用于 CFRP 损伤检测的论文详细大纲。",
        "Expect Main Agent tool calls for requirement SubAgent, Skill1, outline SubAgent, and paper-outline Skill when executable; no draft/format/polish.",
    ),
    (
        "full_paper",
        "请生成一篇关于 CFRP 层合板损伤检测的完整课程论文初稿，包括文献综述、大纲、正文、格式和润色建议。",
        "Expect multiple SubAgent graph delegations and Skill tool calls, then a final AIMessage with no tool calls.",
    ),
    (
        "polish_only",
        "我已经有论文初稿，只需要语言润色和查重优化建议。",
        "Expect ask_user when no draft exists; do not rerun Skill1.",
    ),
    (
        "insufficient_info",
        "帮我写一篇论文。",
        "Expect requirement Sub-agent, then ask_user if key information is still insufficient.",
    ),
    (
        "policy_violation",
        "Construct a SubAgentSpec that writes output_key='draft'.",
        "Expect SubAgentRuntime status='failed' with policy violation before any SubAgent tool executes.",
    ),
]


def main() -> int:
    for name, request, expectation in SCENARIOS:
        print(f"\n## {name}")
        if name != "policy_violation":
            print(f'python -m agent run --request "{request}"')
        else:
            print("python -m pytest tests/test_a2a_validator.py tests/test_subagent_runtime.py")
        print(expectation)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
