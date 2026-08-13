from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from forgeops_agent.errors import AgentError, PolicyError


def run_git(
    repo: Path,
    *args: str,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise AgentError(f"git {' '.join(args)} failed: {detail}")
    return result


def current_branch(repo: Path) -> str:
    return run_git(repo, "branch", "--show-current").stdout.strip()


def head_commit(repo: Path) -> str:
    return run_git(repo, "rev-parse", "HEAD").stdout.strip()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or "task"


def branch_for(task_id: str, title: str) -> str:
    number = task_id.split("-", 1)[1]
    return f"ai/{number}-{slugify(title)}"


def assert_agent_branch(repo: Path, protected_branches: tuple[str, ...]) -> str:
    branch = current_branch(repo)
    protected = {item.lower() for item in protected_branches}
    if branch.lower() in protected or not branch.startswith("ai/"):
        raise PolicyError(f"Agent worktree must use ai/*, found {branch or 'detached HEAD'}")
    return branch


def create_worktree(
    repo: Path,
    worktree: Path,
    branch: str,
    base_ref: str = "HEAD",
) -> str:
    if worktree.exists():
        raise PolicyError(f"Worktree path already exists: {worktree}")
    worktree.parent.mkdir(parents=True, exist_ok=True)
    branch_exists = run_git(repo, "show-ref", "--verify", f"refs/heads/{branch}", check=False)
    if branch_exists.returncode == 0:
        run_git(repo, "worktree", "add", str(worktree), branch)
    else:
        run_git(repo, "worktree", "add", "-b", branch, str(worktree), base_ref)
    return head_commit(worktree)


def changed_files(worktree: Path, base_commit: str) -> list[str]:
    tracked = run_git(worktree, "diff", "--name-only", base_commit, "--").stdout.splitlines()
    untracked = run_git(
        worktree, "ls-files", "--others", "--exclude-standard"
    ).stdout.splitlines()
    return sorted({item.replace("\\", "/") for item in [*tracked, *untracked] if item})


def compact_diff(worktree: Path, base_commit: str, max_chars: int = 30000) -> str:
    result = run_git(
        worktree,
        "diff",
        "--no-ext-diff",
        "--unified=3",
        base_commit,
        "--",
        check=False,
    )
    diff = result.stdout
    for path in run_git(
        worktree, "ls-files", "--others", "--exclude-standard"
    ).stdout.splitlines():
        extra = run_git(worktree, "diff", "--no-index", "--", os.devnull, path, check=False)
        diff += extra.stdout
    if len(diff) > max_chars:
        return diff[:max_chars] + "\n\n[diff truncated by forgeops-agent]\n"
    return diff


def commit_changes(worktree: Path, task_id: str, title: str, paths: list[str]) -> str:
    if not paths:
        raise PolicyError("No task changes to commit")
    before = head_commit(worktree)
    run_git(worktree, "add", "--", *paths)
    staged = run_git(worktree, "diff", "--cached", "--name-only", "--").stdout.splitlines()
    if sorted(staged) != sorted(paths):
        run_git(worktree, "restore", "--staged", "--", *staged, check=False)
        raise PolicyError("Staged file set does not match validated task scope")
    environment = os.environ.copy()
    environment["FORGEOPS_AGENT_VALIDATED"] = "1"
    run_git(worktree, "commit", "-m", f"{task_id}: {title.lower()}", env=environment)
    commit = head_commit(worktree)
    if commit == before:
        raise PolicyError("Git did not create the validated commit")
    return commit


def remove_worktree(repo: Path, worktree: Path) -> None:
    status = run_git(worktree, "status", "--porcelain").stdout.strip()
    if status:
        raise PolicyError("Cleanup refused: worktree contains uncommitted changes")
    run_git(repo, "worktree", "remove", str(worktree))
    run_git(repo, "worktree", "prune")
