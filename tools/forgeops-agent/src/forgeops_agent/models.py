from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any

from forgeops_agent.errors import ConfigurationError

TASK_ID_PATTERN = re.compile(r"^AI-\d{4,}$")
TASK_FIELDS = {
    "id",
    "title",
    "objective",
    "allowed_paths",
    "forbidden_paths",
    "required_checks",
    "max_attempts",
    "timeout_minutes",
    "allow_commit",
    "allow_push",
    "allow_merge",
    "allow_network",
    "risk",
    "depends_on",
    "context_files",
}


class Risk(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TaskStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    FAILED_POLICY = "FAILED_POLICY"
    FAILED_TESTS = "FAILED_TESTS"
    FAILED_SECURITY = "FAILED_SECURITY"
    TIMEOUT = "TIMEOUT"
    INTERRUPTED = "INTERRUPTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


TERMINAL_STATUSES = {
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.FAILED_POLICY,
    TaskStatus.FAILED_TESTS,
    TaskStatus.FAILED_SECURITY,
    TaskStatus.TIMEOUT,
    TaskStatus.INTERRUPTED,
    TaskStatus.APPROVED,
    TaskStatus.REJECTED,
    TaskStatus.CANCELLED,
}


def normalize_task_path(value: str) -> str:
    candidate = value.strip().replace("\\", "/")
    if not candidate or candidate.startswith("/") or re.match(r"^[A-Za-z]:", candidate):
        raise ConfigurationError(f"Task path must be repository-relative: {value!r}")
    path = PurePosixPath(candidate)
    if ".." in path.parts or ".git" in path.parts:
        raise ConfigurationError(f"Unsafe task path: {value!r}")
    normalized = path.as_posix().lstrip("./")
    return normalized.rstrip("/") + ("/" if candidate.endswith("/") else "")


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    objective: str
    allowed_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...] = ()
    required_checks: tuple[str, ...] = ()
    max_attempts: int = 3
    timeout_minutes: int = 60
    allow_commit: bool = True
    allow_push: bool = False
    allow_merge: bool = False
    allow_network: bool = False
    risk: Risk = Risk.LOW
    depends_on: tuple[str, ...] = ()
    context_files: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        required = {"id", "title", "objective", "allowed_paths", "risk"}
        missing = sorted(required - data.keys())
        if missing:
            raise ConfigurationError(f"Missing task fields: {', '.join(missing)}")
        unknown = sorted(data.keys() - TASK_FIELDS)
        if unknown:
            raise ConfigurationError(f"Unknown task fields: {', '.join(unknown)}")
        task_id = str(data["id"]).strip().upper()
        if not TASK_ID_PATTERN.fullmatch(task_id):
            raise ConfigurationError("Task id must match AI-0001")
        allowed_paths = tuple(
            normalize_task_path(str(item))
            for item in cls._list_field(data, "allowed_paths")
        )
        if not allowed_paths:
            raise ConfigurationError("allowed_paths cannot be empty")
        forbidden_paths = tuple(
            normalize_task_path(str(item))
            for item in cls._list_field(data, "forbidden_paths")
        )
        context_files = tuple(
            normalize_task_path(str(item))
            for item in cls._list_field(data, "context_files")
        )
        depends_on = tuple(
            str(item).strip().upper() for item in cls._list_field(data, "depends_on")
        )
        for dependency in depends_on:
            if not TASK_ID_PATTERN.fullmatch(dependency) or dependency == task_id:
                raise ConfigurationError(f"Invalid task dependency: {dependency}")
        risk_value = str(data["risk"]).upper()
        try:
            risk = Risk(risk_value)
        except ValueError as exc:
            raise ConfigurationError(f"Invalid task risk: {risk_value}") from exc
        task = cls(
            id=task_id,
            title=str(data["title"]).strip(),
            objective=str(data["objective"]).strip(),
            allowed_paths=allowed_paths,
            forbidden_paths=forbidden_paths,
            required_checks=tuple(
                str(item).strip() for item in cls._list_field(data, "required_checks")
            ),
            max_attempts=cls._integer_field(data, "max_attempts", 3),
            timeout_minutes=cls._integer_field(data, "timeout_minutes", 60),
            allow_commit=cls._boolean_field(data, "allow_commit", True),
            allow_push=cls._boolean_field(data, "allow_push", False),
            allow_merge=cls._boolean_field(data, "allow_merge", False),
            allow_network=cls._boolean_field(data, "allow_network", False),
            risk=risk,
            depends_on=depends_on,
            context_files=context_files,
        )
        task.validate()
        return task

    @staticmethod
    def _list_field(data: dict[str, Any], name: str) -> list[Any]:
        value = data.get(name, [])
        if not isinstance(value, list):
            raise ConfigurationError(f"{name} must be a YAML list")
        return value

    @staticmethod
    def _boolean_field(data: dict[str, Any], name: str, default: bool) -> bool:
        value = data.get(name, default)
        if not isinstance(value, bool):
            raise ConfigurationError(f"{name} must be true or false")
        return value

    @staticmethod
    def _integer_field(data: dict[str, Any], name: str, default: int) -> int:
        value = data.get(name, default)
        if type(value) is not int:
            raise ConfigurationError(f"{name} must be an integer")
        return value

    def validate(self) -> None:
        if not 3 <= len(self.title) <= 120:
            raise ConfigurationError("Task title must contain between 3 and 120 characters")
        if not 10 <= len(self.objective) <= 4000:
            raise ConfigurationError("Task objective must contain between 10 and 4000 characters")
        if not self.allowed_paths:
            raise ConfigurationError("allowed_paths cannot be empty")
        if len(self.allowed_paths) != len(set(self.allowed_paths)):
            raise ConfigurationError("allowed_paths cannot contain duplicates")
        if not 1 <= self.max_attempts <= 5:
            raise ConfigurationError("max_attempts must be between 1 and 5")
        if not 5 <= self.timeout_minutes <= 480:
            raise ConfigurationError("timeout_minutes must be between 5 and 480")
        if self.allow_push or self.allow_merge:
            raise ConfigurationError("Automatic push and merge are disabled in V1")
        if self.risk is Risk.CRITICAL:
            raise ConfigurationError("CRITICAL tasks cannot be delegated")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["risk"] = self.risk.value
        for key in (
            "allowed_paths",
            "forbidden_paths",
            "required_checks",
            "depends_on",
            "context_files",
        ):
            data[key] = list(data[key])
        return data


@dataclass
class TaskState:
    task_id: str
    status: TaskStatus
    branch: str | None = None
    worktree: str | None = None
    base_commit: str | None = None
    commit: str | None = None
    attempts: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    last_action: str = "queued"
    test_status: str = "NOT_RUN"
    error: str | None = None
    model: str | None = None
    changed_files: list[str] = field(default_factory=list)
    check_results: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskState:
        values = dict(data)
        values["status"] = TaskStatus(values["status"])
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass(frozen=True)
class RunnerResult:
    return_code: int
    timed_out: bool
    stopped: bool
    duration_seconds: float
    log_path: str
    summary: str


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    return_code: int
    duration_seconds: float
    summary: str
