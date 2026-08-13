from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import yaml

from forgeops_agent.errors import ConfigurationError, TaskNotFoundError
from forgeops_agent.models import Task, TaskState, TaskStatus

TASK_DIRECTORIES = ("queue", "running", "completed", "failed")


class TaskStore:
    def __init__(self, ai_root: Path):
        self.ai_root = ai_root
        self.tasks_root = ai_root / "tasks"
        self.state_root = ai_root / "state"
        for name in TASK_DIRECTORIES:
            (self.tasks_root / name).mkdir(parents=True, exist_ok=True)
        self.state_root.mkdir(parents=True, exist_ok=True)

    def load_task_file(self, path: Path) -> Task:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ConfigurationError(f"Task file must contain a YAML mapping: {path}")
        return Task.from_dict(data)

    def find_task_path(self, task_id: str) -> Path:
        normalized = task_id.upper()
        for directory in TASK_DIRECTORIES:
            for path in (self.tasks_root / directory).glob("*.yaml"):
                try:
                    if self.load_task_file(path).id == normalized:
                        return path
                except ConfigurationError:
                    continue
        raise TaskNotFoundError(f"Task not found: {normalized}")

    def load_task(self, task_id: str) -> Task:
        return self.load_task_file(self.find_task_path(task_id))

    def delegate(self, source: Path) -> Task:
        task = self.load_task_file(source)
        try:
            existing = self.find_task_path(task.id)
        except TaskNotFoundError:
            existing = None
        if existing:
            raise ConfigurationError(f"Task already exists: {task.id} ({existing})")
        destination = self.tasks_root / "queue" / f"{task.id}.yaml"
        destination.write_text(
            yaml.safe_dump(task.to_dict(), sort_keys=False, allow_unicode=False),
            encoding="utf-8",
        )
        self.save_state(TaskState(task_id=task.id, status=TaskStatus.QUEUED))
        return task

    def queued(self) -> list[Task]:
        tasks = [self.load_task_file(path) for path in (self.tasks_root / "queue").glob("*.yaml")]
        return sorted(tasks, key=lambda task: task.id)

    def move(self, task_id: str, directory: str) -> Path:
        if directory not in TASK_DIRECTORIES:
            raise ConfigurationError(f"Invalid task directory: {directory}")
        source = self.find_task_path(task_id)
        destination = self.tasks_root / directory / source.name
        if source != destination:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
        return destination

    def state_path(self, task_id: str) -> Path:
        return self.state_root / f"{task_id.upper()}.json"

    def load_state(self, task_id: str) -> TaskState:
        path = self.state_path(task_id)
        if not path.exists():
            return TaskState(task_id=task_id.upper(), status=TaskStatus.QUEUED)
        return TaskState.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save_state(self, state: TaskState) -> None:
        path = self.state_path(state.task_id)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
        temporary.replace(path)

    def dependencies_ready(self, task: Task) -> tuple[bool, list[str]]:
        blocked: list[str] = []
        for dependency in task.depends_on:
            status = self.load_state(dependency).status
            if status not in {TaskStatus.COMPLETED, TaskStatus.APPROVED}:
                blocked.append(f"{dependency}={status.value}")
        return not blocked, blocked

    def recover_interrupted(self) -> list[str]:
        recovered: list[str] = []
        for path in (self.tasks_root / "running").glob("*.yaml"):
            task = self.load_task_file(path)
            state = self.load_state(task.id)
            state.status = TaskStatus.INTERRUPTED
            state.finished_at = datetime.now(UTC).isoformat()
            state.last_action = "recovered after supervisor restart"
            self.save_state(state)
            self.move(task.id, "failed")
            recovered.append(task.id)
        return recovered

