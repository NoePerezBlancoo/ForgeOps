import json
import os
import subprocess
from pathlib import Path

import pytest

from forgeops_agent.errors import LockError, PolicyError
from forgeops_agent.git import (
    assert_agent_branch,
    changed_files,
    create_worktree,
    remove_worktree,
)
from forgeops_agent.locks import FileLock


def test_main_branch_is_blocked_and_ai_branch_is_allowed(git_repo: Path):
    with pytest.raises(PolicyError, match=r"ai/\*"):
        assert_agent_branch(git_repo, ("main", "master", "production"))
    subprocess.run(["git", "switch", "-c", "ai/0001-tests"], cwd=git_repo, check=True)
    assert assert_agent_branch(git_repo, ("main", "master", "production")) == "ai/0001-tests"


def test_worktree_creation_change_detection_and_cleanup(git_repo: Path):
    worktree = git_repo.parent / "worktrees" / "ai-0001"
    base = create_worktree(git_repo, worktree, "ai/0001-tests")
    (worktree / "test.txt").write_text("change\n", encoding="utf-8")
    assert changed_files(worktree, base) == ["test.txt"]
    subprocess.run(["git", "add", "test.txt"], cwd=worktree, check=True)
    subprocess.run(["git", "commit", "-m", "AI-0001: test"], cwd=worktree, check=True)
    remove_worktree(git_repo, worktree)
    assert not worktree.exists()
    branches = subprocess.run(
        ["git", "branch", "--list", "ai/0001-tests"],
        cwd=git_repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "ai/0001-tests" in branches


def test_cleanup_refuses_dirty_worktree(git_repo: Path):
    worktree = git_repo.parent / "worktrees" / "ai-0002"
    create_worktree(git_repo, worktree, "ai/0002-tests")
    (worktree / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(PolicyError, match="uncommitted"):
        remove_worktree(git_repo, worktree)


def test_lock_prevents_second_owner(tmp_path: Path):
    path = tmp_path / "task.lock"
    with FileLock(path):
        with pytest.raises(LockError):
            FileLock(path).acquire()
    assert not path.exists()


def test_stale_lock_is_reclaimed(tmp_path: Path):
    path = tmp_path / "task.lock"
    path.write_text(json.dumps({"pid": 99999999}), encoding="utf-8")
    lock = FileLock(path).acquire()
    assert json.loads(path.read_text(encoding="utf-8"))["pid"] == os.getpid()
    lock.release()
