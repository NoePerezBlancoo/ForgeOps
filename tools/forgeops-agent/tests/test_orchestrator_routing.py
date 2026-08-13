from __future__ import annotations

import subprocess
from pathlib import Path

import yaml
from conftest import make_config

from forgeops_agent.models import CheckResult, RunnerResult, TaskStatus
from forgeops_agent.orchestrator import Orchestrator


class ControlledRunner:
    def __init__(self):
        self.models: list[str] = []

    def run(self, task, worktree, prompt, log_path, model):
        self.models.append(model)
        target = worktree / "backend" / "tests" / "test_auth.py"
        target.write_text(f"def test_attempt():\n    assert {len(self.models)} == 2\n")
        return RunnerResult(0, False, False, 0.1, str(log_path), "controlled")

    def stop(self, task_id):
        return None


class ControlledChecks:
    def __init__(self):
        self.calls = 0

    def format_changed_python(self, task_id, worktree, paths):
        return []

    def run_all(self, task, worktree, paths):
        self.calls += 1
        passed = self.calls == 2
        return [CheckResult("controlled-quality", passed, 0 if passed else 1, 0.1, "fixture")]


def test_orchestrator_runs_controlled_qwen_to_devstral_fallback(
    git_repo: Path, sample_task
):
    target = git_repo / "backend" / "tests" / "test_auth.py"
    target.parent.mkdir(parents=True)
    target.write_text("def test_existing():\n    assert True\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Add fixture"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    config = make_config(git_repo)
    source = git_repo / "task.yaml"
    source.write_text(yaml.safe_dump(sample_task.to_dict(), sort_keys=False), encoding="utf-8")
    orchestrator = Orchestrator(config)
    runner = ControlledRunner()
    orchestrator.runner = runner
    orchestrator.checks = ControlledChecks()
    orchestrator.store.delegate(source)

    state = orchestrator.run_task(sample_task.id)

    assert state.status is TaskStatus.COMPLETED
    assert runner.models == ["qwen-test", "devstral-test"]
    assert state.fallback_used is True
    assert state.attempt_history[0]["status"] == "FAILED_TESTS"
    assert state.attempt_history[1]["status"] == "COMPLETED"
    assert state.attempt_history[1]["is_fallback"] is True
    orchestrator.cleanup(sample_task.id)
