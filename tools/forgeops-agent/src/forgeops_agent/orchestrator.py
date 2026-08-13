from __future__ import annotations

import json
import re
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from forgeops_agent.checks import CheckRunner
from forgeops_agent.config import OrchestratorConfig
from forgeops_agent.errors import PolicyError
from forgeops_agent.git import (
    assert_agent_branch,
    branch_for,
    changed_files,
    commit_changes,
    compact_diff,
    create_worktree,
    head_commit,
    remove_worktree,
    run_git,
)
from forgeops_agent.locks import FileLock
from forgeops_agent.models import TERMINAL_STATUSES, Task, TaskState, TaskStatus
from forgeops_agent.policy import scan_secrets, validate_changed_paths, validate_task_policy
from forgeops_agent.reports import write_review_package, write_task_report
from forgeops_agent.runner import AiderRunner
from forgeops_agent.store import TaskStore
from forgeops_agent.system import resource_snapshot, resource_violations


class Orchestrator:
    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.store = TaskStore(config.ai_root)
        if config.agent_provider != "aider":
            raise PolicyError(f"Unsupported local agent provider: {config.agent_provider}")
        self.runner = AiderRunner(config)
        self.checks = CheckRunner(config.repo_root)

    def delegate(self, source: Path) -> Task:
        task = self.store.load_task_file(source)
        validate_task_policy(task, self.config.protected_path_prefixes)
        return self.store.delegate(source)

    def run_task(
        self,
        task_id: str,
        *,
        allow_medium: bool = False,
        allow_high: bool = False,
    ) -> TaskState:
        if (self.config.ai_root / "STOP").exists():
            raise PolicyError("Kill switch .ai/STOP is active")
        task = self.store.load_task(task_id)
        validate_task_policy(
            task,
            self.config.protected_path_prefixes,
            allow_medium=allow_medium,
            allow_high=allow_high,
        )
        ready, blocked = self.store.dependencies_ready(task)
        if not ready:
            raise PolicyError("Dependencies not ready: " + ", ".join(blocked))
        execution_lock = FileLock(self.config.ai_root / "locks" / "execution.lock")
        task_lock = FileLock(self.config.ai_root / "locks" / f"{task.id}.lock")
        with execution_lock, task_lock:
            return self._execute(task)

    def _execute(self, task: Task) -> TaskState:
        state = self.store.load_state(task.id)
        if state.status in {TaskStatus.APPROVED, TaskStatus.COMPLETED}:
            raise PolicyError(f"Task is already {state.status.value}")
        if state.attempts >= task.max_attempts:
            raise PolicyError("Task retry limit reached")
        resources = resource_snapshot(self.config.repo_root)
        violations = resource_violations(resources, self.config)
        if violations:
            raise PolicyError("Resource guard blocked task: " + "; ".join(violations))

        state.status = TaskStatus.RUNNING
        state.attempts += 1
        state.started_at = datetime.now(UTC).isoformat()
        state.finished_at = None
        state.last_action = "preparing isolated worktree"
        state.model = self.config.primary_model
        state.error = None
        self.store.save_state(state)
        self.store.move(task.id, "running")
        self._write_status(state, resources)

        try:
            worktree = self._prepare_worktree(task, state)
            assert_agent_branch(worktree, self.config.protected_branches)
            if state.base_commit and head_commit(worktree) != state.base_commit:
                raise PolicyError("Agent branch contains an unvalidated commit")
            prompt = self._write_prompt(task, state, worktree)
            models = [self.config.primary_model]
            if (
                self.config.fallback_model
                and self.config.fallback_model != self.config.primary_model
            ):
                models.append(self.config.fallback_model)
            paths: list[str] = []
            for index, model in enumerate(models):
                state.model = model
                state.last_action = f"local agent running ({model})"
                self.store.save_state(state)
                self._write_status(state, resource_snapshot(self.config.repo_root))
                log_model = re.sub(r"[^a-z0-9]+", "-", model.lower()).strip("-")
                result = self.runner.run(
                    task,
                    worktree,
                    prompt,
                    self.config.ai_root / "logs" / f"{task.id}-{log_model}.log",
                    model,
                )
                if result.timed_out:
                    return self._finish(
                        task, state, TaskStatus.TIMEOUT, "Task timeout reached"
                    )
                if result.stopped:
                    return self._finish(
                        task, state, TaskStatus.CANCELLED, "Kill switch activated"
                    )
                paths = changed_files(worktree, state.base_commit or "HEAD")
                if result.return_code == 0 and paths:
                    break
                if paths or index == len(models) - 1:
                    detail = (
                        f"Agent exited with {result.return_code}: {result.summary[-1000:]}"
                        if result.return_code != 0
                        else "Agent produced no changes"
                    )
                    return self._finish(task, state, TaskStatus.FAILED, detail)
                state.last_action = f"trying fallback after no changes from {model}"
                self.store.save_state(state)

            state.last_action = "validating changed paths"
            state.changed_files = paths
            path_policy = validate_changed_paths(
                task, paths, self.config.protected_path_prefixes
            )
            if not path_policy.valid:
                return self._finish(
                    task,
                    state,
                    TaskStatus.FAILED_POLICY,
                    "; ".join(path_policy.violations),
                )
            security = scan_secrets(worktree, paths)
            if not security.valid:
                return self._finish(
                    task,
                    state,
                    TaskStatus.FAILED_SECURITY,
                    "; ".join(security.violations),
                )

            state.last_action = "applying deterministic formatting"
            self.store.save_state(state)
            checks = self.checks.format_changed_python(task.id, worktree, paths)
            if not all(item.passed for item in checks):
                state.check_results = [asdict(item) for item in checks]
                state.test_status = "FAIL"
                failure = next(item for item in checks if not item.passed)
                return self._finish(
                    task,
                    state,
                    TaskStatus.FAILED_TESTS,
                    f"{failure.name}: {failure.summary}",
                )
            paths = changed_files(worktree, state.base_commit or "HEAD")
            state.changed_files = paths
            path_policy = validate_changed_paths(
                task, paths, self.config.protected_path_prefixes
            )
            security = scan_secrets(worktree, paths)
            if not path_policy.valid:
                return self._finish(
                    task,
                    state,
                    TaskStatus.FAILED_POLICY,
                    "; ".join(path_policy.violations),
                )
            if not security.valid:
                return self._finish(
                    task,
                    state,
                    TaskStatus.FAILED_SECURITY,
                    "; ".join(security.violations),
                )
            state.last_action = "running quality checks"
            self.store.save_state(state)
            checks.extend(self.checks.run_all(task, worktree, paths))
            state.check_results = [asdict(item) for item in checks]
            state.test_status = "PASS" if all(item.passed for item in checks) else "FAIL"
            if not all(item.passed for item in checks):
                failure = next(item for item in checks if not item.passed)
                return self._finish(
                    task,
                    state,
                    TaskStatus.FAILED_TESTS,
                    f"{failure.name}: {failure.summary}",
                )
            if task.allow_commit:
                state.last_action = "creating validated local commit"
                state.commit = commit_changes(worktree, task.id, task.title, paths)
            return self._finish(task, state, TaskStatus.COMPLETED)
        except Exception as exc:
            return self._finish(task, state, TaskStatus.FAILED, str(exc))

    def _prepare_worktree(self, task: Task, state: TaskState) -> Path:
        if state.worktree and Path(state.worktree).exists():
            return Path(state.worktree)
        branch = state.branch or branch_for(task.id, task.title)
        worktree = self.config.worktrees_root / task.id.lower()
        base_commit = create_worktree(self.config.repo_root, worktree, branch)
        state.branch = branch
        state.worktree = str(worktree)
        state.base_commit = base_commit
        self.store.save_state(state)
        return worktree

    def _write_prompt(self, task: Task, state: TaskState, worktree: Path) -> Path:
        task_state = self.config.ai_root / "state" / task.id
        task_state.mkdir(parents=True, exist_ok=True)
        feedback_path = task_state / "feedback.md"
        feedback = feedback_path.read_text(encoding="utf-8") if feedback_path.exists() else "None"
        base = (self.config.ai_root / "prompts" / "base.md").read_text(encoding="utf-8")
        prompt = f"""{base}

## Assigned task

Task: {task.id}
Title: {task.title}
Risk: {task.risk.value}
Branch: {state.branch}
Attempt: {state.attempts}/{task.max_attempts}

Objective:

{task.objective}

Allowed paths:
{self._bullets(task.allowed_paths)}

Forbidden paths:
{self._bullets((*self.config.protected_path_prefixes, *task.forbidden_paths))}

Required checks performed by the supervisor after you finish:
{self._bullets(task.required_checks or ('automatic checks selected from changed paths',))}

Context files you may inspect:
{self._bullets(task.context_files or task.allowed_paths)}

Implementation instructions:
- Edit only the explicitly supplied editable files.
- Treat all read-only files as context; never reproduce or modify them.
- Return after applying the smallest complete change. The supervisor runs trusted checks.

Codex feedback from a previous attempt:

{feedback}

Work only inside `/workspace`. Do not create commits. Finish after implementing and locally inspecting the scoped change.
"""
        path = task_state / "prompt.md"
        path.write_text(prompt, encoding="utf-8")
        return path

    @staticmethod
    def _bullets(items) -> str:
        return "\n".join(f"- `{item}`" for item in items) or "- None"

    def _finish(
        self,
        task: Task,
        state: TaskState,
        status: TaskStatus,
        error: str | None = None,
    ) -> TaskState:
        state.status = status
        state.finished_at = datetime.now(UTC).isoformat()
        state.last_action = "finished"
        state.error = error
        self.store.save_state(state)
        destination = "completed" if status in {TaskStatus.COMPLETED, TaskStatus.APPROVED} else "failed"
        self.store.move(task.id, destination)
        write_task_report(self.config.ai_root, task, state)
        self._write_status(state, resource_snapshot(self.config.repo_root))
        return state

    def run_next(self, **risk_flags) -> TaskState | None:
        for task in self.store.queued():
            ready, _ = self.store.dependencies_ready(task)
            if ready:
                return self.run_task(task.id, **risk_flags)
        return None

    def supervise(self, watch: bool = False, **risk_flags) -> None:
        lock_path = self.config.ai_root / "locks" / "supervisor.lock"
        with FileLock(lock_path):
            with FileLock(self.config.ai_root / "locks" / "execution.lock"):
                running = list((self.config.ai_root / "tasks" / "running").glob("*.yaml"))
                for path in running:
                    self.runner.stop(self.store.load_task_file(path).id)
                self.store.recover_interrupted()
            while not (self.config.ai_root / "STOP").exists():
                state = self.run_next(**risk_flags)
                if state is None:
                    self._write_idle_status()
                    if not watch:
                        return
                    time.sleep(self.config.idle_poll_seconds)

    def retry(self, task_id: str, feedback_path: Path) -> TaskState:
        task = self.store.load_task(task_id)
        state = self.store.load_state(task.id)
        if state.attempts >= task.max_attempts:
            raise PolicyError("Task retry limit reached")
        feedback = feedback_path.read_text(encoding="utf-8")
        destination = self.config.ai_root / "state" / task.id / "feedback.md"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(feedback, encoding="utf-8")
        state.status = TaskStatus.QUEUED
        state.error = None
        self.store.save_state(state)
        self.store.move(task.id, "queue")
        return state

    def approve(self, task_id: str) -> TaskState:
        task = self.store.load_task(task_id)
        state = self.store.load_state(task.id)
        if state.status is not TaskStatus.COMPLETED:
            raise PolicyError("Only COMPLETED tasks can be approved")
        state.status = TaskStatus.APPROVED
        state.last_action = "approved by Codex"
        self.store.save_state(state)
        write_task_report(self.config.ai_root, task, state)
        return state

    def reject(self, task_id: str, reason: str) -> TaskState:
        task = self.store.load_task(task_id)
        state = self.store.load_state(task.id)
        if state.status not in {TaskStatus.COMPLETED, TaskStatus.APPROVED}:
            raise PolicyError("Only completed work can be rejected")
        state.status = TaskStatus.REJECTED
        state.error = reason
        state.last_action = "rejected by Codex"
        self.store.save_state(state)
        self.store.move(task.id, "failed")
        write_task_report(self.config.ai_root, task, state)
        return state

    def review_package(self, task_id: str) -> Path:
        task = self.store.load_task(task_id)
        state = self.store.load_state(task.id)
        if not state.worktree or not state.base_commit:
            raise PolicyError("Task has no worktree or base commit")
        diff = compact_diff(Path(state.worktree), state.base_commit)
        return write_review_package(self.config.ai_root, task, state, diff)

    def cleanup(self, task_id: str) -> TaskState:
        task = self.store.load_task(task_id)
        state = self.store.load_state(task.id)
        if state.status not in TERMINAL_STATUSES:
            raise PolicyError(f"Cleanup refused for state {state.status.value}")
        if state.worktree and Path(state.worktree).exists():
            remove_worktree(self.config.repo_root, Path(state.worktree))
        state.worktree = None
        state.last_action = "worktree cleaned; branch preserved"
        self.store.save_state(state)
        return state

    def prepare_merge(self, task_id: str) -> dict[str, object]:
        task = self.store.load_task(task_id)
        state = self.store.load_state(task.id)
        if state.status is not TaskStatus.APPROVED:
            raise PolicyError("Task must be APPROVED before prepare-merge")
        if not state.worktree or not state.branch:
            raise PolicyError("Task worktree is not available")
        worktree = Path(state.worktree)
        clean = not run_git(worktree, "status", "--porcelain").stdout.strip()
        main_is_ancestor = (
            run_git(worktree, "merge-base", "--is-ancestor", "main", state.branch, check=False).returncode
            == 0
        )
        return {
            "task": task.id,
            "approved": True,
            "clean": clean,
            "main_is_ancestor": main_is_ancestor,
            "ready": clean and main_is_ancestor,
            "branch": state.branch,
            "commit": state.commit,
        }

    def stop_all(self) -> None:
        (self.config.ai_root / "STOP").write_text(
            f"Stopped at {datetime.now(UTC).isoformat()}\n", encoding="utf-8"
        )
        for path in (self.config.ai_root / "tasks" / "running").glob("*.yaml"):
            task = self.store.load_task_file(path)
            self.runner.stop(task.id)

    def cancel(self, task_id: str) -> TaskState:
        task = self.store.load_task(task_id)
        self.runner.stop(task.id)
        state = self.store.load_state(task.id)
        return self._finish(task, state, TaskStatus.CANCELLED, "Cancelled by supervisor")

    def _write_status(self, state: TaskState, resources: dict) -> None:
        payload = {
            "current_task": state.task_id,
            "status": state.status.value,
            "runtime": "Aider in isolated Docker container",
            "model": state.model,
            "attempt": state.attempts,
            "last_action": state.last_action,
            "test_status": state.test_status,
            "resources": resources,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        (self.config.ai_root / "status.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    def _write_idle_status(self) -> None:
        payload = {
            "current_task": None,
            "status": "IDLE",
            "model": self.config.primary_model,
            "resources": resource_snapshot(self.config.repo_root),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        (self.config.ai_root / "status.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
