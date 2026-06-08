from __future__ import annotations

import asyncio
import json

from middleware.guardrails import GuardrailsMiddleware, check_command


class FakeToolRequest:
    def __init__(self, name: str, args: dict) -> None:
        self.tool_call = {"id": "call-1", "name": name, "args": args}


def test_check_command_allows_whitelisted_skill_script():
    decision = check_command(
        "python skill_packs/academic-paper-writing/skills/literature-review/scripts/run.py "
        "--input input.json --output output.json"
    )

    assert decision.allowed is True


def test_check_command_allows_virtual_skill_script_path():
    decision = check_command(
        "python /skill_packs/academic-paper-writing/skills/literature-review/scripts/run.py "
        "--input /.writeagent/projects/default/artifacts/input.json "
        "--output /.writeagent/projects/default/artifacts/output.json"
    )

    assert decision.allowed is True


def test_check_command_blocks_non_whitelisted_command():
    decision = check_command('python -c "print(123)"')

    assert decision.allowed is False
    assert decision.reason == "Command is not in the execute_bash whitelist."


def test_guardrails_middleware_blocks_non_whitelisted_execute_bash(tmp_path):
    middleware = GuardrailsMiddleware([tmp_path], repo_root=tmp_path)
    called = False

    def handler(_request):
        nonlocal called
        called = True
        return {"status": "ok"}

    result = middleware.wrap_tool_call(FakeToolRequest("execute_bash", {"command": 'python -c "print(123)"'}), handler)

    payload = json.loads(result.content)
    assert called is False
    assert payload == {
        "status": "blocked",
        "reason": "Command is not in the execute_bash whitelist.",
        "command": 'python -c "print(123)"',
        "cwd": None,
    }


def test_guardrails_middleware_async_blocks_non_whitelisted_execute_bash(tmp_path):
    middleware = GuardrailsMiddleware([tmp_path], repo_root=tmp_path)
    called = False

    async def handler(_request):
        nonlocal called
        called = True
        return {"status": "ok"}

    result = asyncio.run(
        middleware.awrap_tool_call(
            FakeToolRequest("execute_bash", {"command": 'python -c "print(123)"'}),
            handler,
        )
    )

    payload = json.loads(result.content)
    assert called is False
    assert payload["status"] == "blocked"
    assert payload["reason"] == "Command is not in the execute_bash whitelist."


def test_guardrails_middleware_blocks_cwd_outside_allowed_roots(tmp_path):
    middleware = GuardrailsMiddleware([tmp_path / "workspace"], repo_root=tmp_path / "workspace")
    outside = tmp_path / "outside"
    outside.mkdir()
    called = False

    def handler(_request):
        nonlocal called
        called = True
        return {"status": "ok"}

    result = middleware.wrap_tool_call(
        FakeToolRequest(
            "execute_bash",
            {
                "command": "python skill_packs/test-pack/skills/test-skill/scripts/run.py",
                "cwd": str(outside),
            },
        ),
        handler,
    )

    payload = json.loads(result.content)
    assert called is False
    assert payload["status"] == "blocked"
    assert payload["command"] == "python skill_packs/test-pack/skills/test-skill/scripts/run.py"
    assert payload["cwd"] == str(outside)
    assert "Path is outside allowed roots" in payload["reason"]


def test_guardrails_middleware_allows_whitelisted_execute_bash(tmp_path):
    middleware = GuardrailsMiddleware([tmp_path], repo_root=tmp_path)
    called = False

    def handler(_request):
        nonlocal called
        called = True
        return {"status": "ok"}

    result = middleware.wrap_tool_call(
        FakeToolRequest(
            "execute_bash",
            {
                "command": (
                    "python skill_packs/academic-paper-writing/skills/literature-review/scripts/run.py "
                    "--input input.json --output output.json"
                ),
                "cwd": str(tmp_path),
            },
        ),
        handler,
    )

    assert called is True
    assert result == {"status": "ok"}


def test_guardrails_middleware_maps_virtual_root_cwd(tmp_path):
    middleware = GuardrailsMiddleware([tmp_path], repo_root=tmp_path)
    called = False

    def handler(_request):
        nonlocal called
        called = True
        return {"status": "ok"}

    result = middleware.wrap_tool_call(
        FakeToolRequest(
            "execute_bash",
            {
                "command": (
                    "python /skill_packs/academic-paper-writing/skills/literature-review/scripts/run.py "
                    "--input /.writeagent/projects/default/artifacts/input.json "
                    "--output /.writeagent/projects/default/artifacts/output.json"
                ),
                "cwd": "/",
            },
        ),
        handler,
    )

    assert called is True
    assert result == {"status": "ok"}


def test_guardrails_middleware_async_allows_whitelisted_execute_bash(tmp_path):
    middleware = GuardrailsMiddleware([tmp_path], repo_root=tmp_path)
    called = False

    async def handler(_request):
        nonlocal called
        called = True
        return {"status": "ok"}

    result = asyncio.run(
        middleware.awrap_tool_call(
            FakeToolRequest(
                "execute_bash",
                {
                    "command": (
                        "python skill_packs/academic-paper-writing/skills/literature-review/scripts/run.py "
                        "--input input.json --output output.json"
                    ),
                    "cwd": str(tmp_path),
                },
            ),
            handler,
        )
    )

    assert called is True
    assert result == {"status": "ok"}


def test_guardrails_middleware_passes_through_other_tools():
    middleware = GuardrailsMiddleware([], repo_root=".")
    called = False

    def handler(_request):
        nonlocal called
        called = True
        return {"status": "ok"}

    result = middleware.wrap_tool_call(FakeToolRequest("inspect_progress", {}), handler)

    assert called is True
    assert result == {"status": "ok"}
