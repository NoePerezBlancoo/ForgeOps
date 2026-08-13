import json
import subprocess
import sys
from pathlib import Path


def run_hook(repo_root: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(repo_root / ".openhands" / "hooks" / "policy.py")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )


def test_hook_blocks_dangerous_command():
    repo_root = Path(__file__).resolve().parents[3]
    result = run_hook(
        repo_root,
        {
            "tool_name": "terminal",
            "tool_input": {"command": "git push --force origin main"},
            "working_dir": "/workspace",
        },
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["decision"] == "deny"


def test_hook_allows_safe_test_command():
    repo_root = Path(__file__).resolve().parents[3]
    result = run_hook(
        repo_root,
        {
            "tool_name": "terminal",
            "tool_input": {"command": "pytest -q tests/test_auth.py"},
            "working_dir": "/workspace",
        },
    )
    assert result.returncode == 0

