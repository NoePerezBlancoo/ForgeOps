from pathlib import Path

from forgeops_agent.checks import CheckRunner


def test_backend_container_mounts_live_worktree_without_network(tmp_path: Path):
    command = CheckRunner._backend_container_command(
        tmp_path,
        "forgeops-ai-check:test",
        ["pytest", "-q", "tests/test_request_context.py"],
    )

    assert command[:6] == ["docker", "run", "--rm", "--network", "none", "-v"]
    assert f"{tmp_path / 'backend'}:/app" in command
    assert command[command.index("--entrypoint") + 1] == "pytest"
    assert command[-3:] == [
        "forgeops-ai-check:test",
        "-q",
        "tests/test_request_context.py",
    ]
