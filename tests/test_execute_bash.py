from __future__ import annotations

from tools.execute_bash import execute_bash


def _write_skill_script(tmp_path, content: str) -> str:
    script = tmp_path / "skill_packs" / "test-pack" / "skills" / "test-skill" / "scripts" / "run.py"
    script.parent.mkdir(parents=True)
    script.write_text(content, encoding="utf-8")
    return "skill_packs/test-pack/skills/test-skill/scripts/run.py"


def test_execute_bash_safe_command(tmp_path):
    script = _write_skill_script(tmp_path, "print(123)")
    result = execute_bash(f"python {script}", cwd=str(tmp_path), repo_root=tmp_path)
    assert result.status == "ok"
    assert result.exit_code == 0
    assert "123" in result.stdout


def test_execute_bash_timeout(tmp_path):
    script = _write_skill_script(tmp_path, "import time; time.sleep(2)")
    result = execute_bash(f"python {script}", cwd=str(tmp_path), repo_root=tmp_path, timeout_sec=1)
    assert result.status == "timeout"


def test_execute_bash_runs_non_whitelisted_command_when_called_directly(tmp_path):
    result = execute_bash('python -c "print(123)"', cwd=str(tmp_path), repo_root=tmp_path)
    assert result.status == "ok"
    assert "123" in result.stdout
