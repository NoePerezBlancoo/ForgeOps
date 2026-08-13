from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from forgeops_agent.config import OrchestratorConfig
from forgeops_agent.models import Risk, Task


@pytest.fixture
def sample_task() -> Task:
    return Task(
        id="AI-0001",
        title="Improve tests",
        objective="Add one focused test without changing production code.",
        allowed_paths=("backend/tests/",),
        forbidden_paths=("backend/alembic/",),
        required_checks=("backend-ruff", "pytest:tests/test_auth.py"),
        risk=Risk.LOW,
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "ForgeOps"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "ForgeOps Tests"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "tests@forgeops.local"], cwd=repo, check=True)
    (repo / "README.md").write_text("ForgeOps\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo, check=True, capture_output=True)
    return repo


def make_config(repo: Path) -> OrchestratorConfig:
    ai_root = repo / ".ai"
    for directory in (
        "tasks/queue",
        "tasks/running",
        "tasks/completed",
        "tasks/failed",
        "state",
        "locks",
        "reports",
        "prompts",
    ):
        (ai_root / directory).mkdir(parents=True, exist_ok=True)
    (ai_root / "prompts" / "base.md").write_text("Base agent policy", encoding="utf-8")
    return OrchestratorConfig(
        repo_root=repo,
        ai_root=ai_root,
        worktrees_root=repo.parent / "ForgeOps-agent-worktrees",
        agent_provider="aider",
        agent_image="forgeops-local-agent:test",
        gateway_image="forgeops-ollama-gateway:test",
        agent_version="0.86.0",
        primary_model="test-model",
        fallback_model=None,
        ollama_url="http://127.0.0.1:11434",
        context_tokens=32768,
        max_parallel_tasks=1,
        max_iterations=10,
        default_timeout_minutes=10,
        idle_poll_seconds=1,
        protected_branches=("main", "master", "production"),
        protected_path_prefixes=(".git/", ".ai/", "deploy/", ".env.production"),
        automatic_risks=("LOW",),
        max_cpu_percent=100,
        min_free_memory_gb=0,
        min_free_disk_gb=0,
        max_gpu_temperature_c=100,
        container_cpus=1,
        container_memory="1g",
        log_max_bytes=1024,
    )
