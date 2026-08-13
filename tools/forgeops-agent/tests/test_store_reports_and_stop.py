from pathlib import Path

import pytest
import yaml
from conftest import make_config

from forgeops_agent.errors import PolicyError
from forgeops_agent.models import TaskState, TaskStatus
from forgeops_agent.orchestrator import Orchestrator
from forgeops_agent.reports import write_review_package, write_task_report
from forgeops_agent.store import TaskStore


def write_task(path: Path, task) -> None:
    path.write_text(yaml.safe_dump(task.to_dict(), sort_keys=False), encoding="utf-8")


def test_queue_and_dependency_state(tmp_path: Path, sample_task):
    store = TaskStore(tmp_path / ".ai")
    source = tmp_path / "task.yaml"
    dependent = type(sample_task)(
        **{**sample_task.__dict__, "id": "AI-0002", "depends_on": ("AI-0001",)}
    )
    write_task(source, dependent)
    store.delegate(source)
    assert [task.id for task in store.queued()] == ["AI-0002"]
    assert store.dependencies_ready(dependent) == (False, ["AI-0001=QUEUED"])
    store.save_state(TaskState(task_id="AI-0001", status=TaskStatus.COMPLETED))
    assert store.dependencies_ready(dependent) == (True, [])


def test_running_task_is_recovered_as_interrupted(tmp_path: Path, sample_task):
    store = TaskStore(tmp_path / ".ai")
    source = tmp_path / "task.yaml"
    write_task(source, sample_task)
    store.delegate(source)
    store.move(sample_task.id, "running")
    state = store.load_state(sample_task.id)
    state.status = TaskStatus.RUNNING
    store.save_state(state)
    assert store.recover_interrupted() == [sample_task.id]
    assert store.load_state(sample_task.id).status is TaskStatus.INTERRUPTED
    assert "failed" in str(store.find_task_path(sample_task.id))


def test_reports_are_compact_and_machine_readable(tmp_path: Path, sample_task):
    state = TaskState(
        task_id=sample_task.id,
        status=TaskStatus.COMPLETED,
        branch="ai/0001-tests",
        commit="abc123",
        changed_files=["backend/tests/test_auth.py"],
        test_status="PASS",
        model="qwen-test",
        routing_primary="qwen-test",
        routing_fallback="devstral-test",
        routing_reason="Configured LOW routing",
        attempt_history=[
            {
                "attempt": 1,
                "model_alias": "qwen",
                "model": "qwen-test",
                "duration_seconds": 3.2,
                "agent_duration_seconds": 3.0,
                "status": "COMPLETED",
                "checks": [
                    {"name": "backend-ruff", "passed": True, "summary": "ok"}
                ],
                "is_fallback": False,
                "resources_after": {"memory_available_gb": 8, "gpu": {}},
            }
        ],
    )
    markdown, payload = write_task_report(tmp_path / ".ai", sample_task, state)
    review = write_review_package(tmp_path / ".ai", sample_task, state, "+assert True")
    assert "COMPLETED" in markdown.read_text(encoding="utf-8")
    assert "# Model routing" in markdown.read_text(encoding="utf-8")
    assert "## Attempt 1" in markdown.read_text(encoding="utf-8")
    assert '"review_required": true' in payload.read_text(encoding="utf-8")
    assert '"first_pass_accepted": false' in payload.read_text(encoding="utf-8")
    assert "+assert True" in review.read_text(encoding="utf-8")


def test_stop_blocks_new_task(git_repo: Path, sample_task):
    config = make_config(git_repo)
    source = git_repo / "task.yaml"
    write_task(source, sample_task)
    orchestrator = Orchestrator(config)
    orchestrator.store.delegate(source)
    (config.ai_root / "STOP").write_text("test\n", encoding="utf-8")
    with pytest.raises(PolicyError, match="STOP"):
        orchestrator.run_task(sample_task.id)


def test_cleanup_accepts_terminal_failed_state(git_repo: Path, sample_task):
    config = make_config(git_repo)
    source = git_repo / "task.yaml"
    write_task(source, sample_task)
    orchestrator = Orchestrator(config)
    orchestrator.store.delegate(source)
    orchestrator.store.move(sample_task.id, "failed")
    state = orchestrator.store.load_state(sample_task.id)
    state.status = TaskStatus.FAILED
    orchestrator.store.save_state(state)

    cleaned = orchestrator.cleanup(sample_task.id)

    assert cleaned.status is TaskStatus.FAILED
    assert cleaned.last_action == "worktree cleaned; branch preserved"


def test_codex_can_retry_qwen_work_with_devstral(
    git_repo: Path, sample_task, tmp_path: Path
):
    config = make_config(git_repo)
    source = git_repo / "task.yaml"
    write_task(source, sample_task)
    orchestrator = Orchestrator(config)
    orchestrator.store.delegate(source)
    orchestrator.store.move(sample_task.id, "completed")
    state = orchestrator.store.load_state(sample_task.id)
    state.status = TaskStatus.COMPLETED
    state.attempts = 1
    state.attempt_history = [{"model_alias": "qwen", "status": "COMPLETED"}]
    orchestrator.store.save_state(state)
    feedback = tmp_path / "feedback.md"
    feedback.write_text("Tighten the assertions without changing scope.", encoding="utf-8")

    retried = orchestrator.retry(sample_task.id, feedback, model_override="devstral")

    assert retried.status is TaskStatus.QUEUED
    assert retried.next_model_override == "devstral"
    assert retried.codex_correction_required is True
    assert retried.retry_count == 1
    assert retried.fallback_used is True
