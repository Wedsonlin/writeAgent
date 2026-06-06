from __future__ import annotations

from tools.execute_bash import execute_bash


def test_execute_bash_safe_command(tmp_path):
    result = execute_bash('python -c "print(123)"', cwd=str(tmp_path), repo_root=tmp_path)
    assert result.status == "ok"
    assert result.exit_code == 0
    assert "123" in result.stdout


def test_execute_bash_blocks_dangerous_command(tmp_path):
    result = execute_bash("rm -rf .", cwd=str(tmp_path), repo_root=tmp_path)
    assert result.status == "blocked"


def test_execute_bash_timeout(tmp_path):
    result = execute_bash('python -c "import time; time.sleep(2)"', cwd=str(tmp_path), repo_root=tmp_path, timeout_sec=1)
    assert result.status == "timeout"


def test_execute_bash_blocks_cwd_escape(tmp_path):
    outside = tmp_path.parent
    result = execute_bash('python -c "print(1)"', cwd=str(outside), repo_root=tmp_path)
    assert result.status == "blocked"
