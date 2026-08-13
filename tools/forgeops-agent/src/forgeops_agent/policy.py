from __future__ import annotations

import re
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath

from forgeops_agent.errors import PolicyError
from forgeops_agent.models import Risk, Task

SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "Railway token": re.compile(r"(?i)RAILWAY_(?:TOKEN|API_TOKEN)\s*[:=]\s*['\"]?[A-Za-z0-9_-]{20,}"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "credential URL": re.compile(r"(?i)(?:postgres(?:ql)?|redis|smtp)://[^\s/:]+:[^\s/@]+@"),
    "JWT or application secret": re.compile(
        r"(?i)(?:SECRET_KEY|JWT_SECRET|S3_SECRET_KEY|SMTP_PASSWORD)\s*[:=]\s*['\"]?(?!replace|fake|test|local)[^\s'\"]{20,}"
    ),
    "generic API token": re.compile(
        r"(?i)(?:api[_-]?key|access[_-]?token|refresh[_-]?token)\s*[:=]\s*['\"]?(?!replace|fake|test|local)[A-Za-z0-9_./+=-]{24,}"
    ),
}


SENSITIVE_PREFIXES = (
    "deploy/",
    ".github/",
    "backend/alembic/",
    "backend/migrations/",
    "backend/app/auth/",
    "backend/app/operators/",
    "backend/app/core/security",
)


@dataclass(frozen=True)
class PolicyResult:
    valid: bool
    violations: tuple[str, ...]


def path_matches(path: str, rule: str) -> bool:
    normalized = PurePosixPath(path).as_posix()
    clean_rule = rule.replace("\\", "/")
    if any(character in clean_rule for character in "*?["):
        return fnmatch(normalized, clean_rule)
    prefix = clean_rule.rstrip("/")
    return normalized == prefix or normalized.startswith(prefix + "/")


def validate_task_policy(
    task: Task,
    always_forbidden: tuple[str, ...],
    allow_medium: bool = False,
    allow_high: bool = False,
) -> None:
    if task.risk is Risk.MEDIUM and not allow_medium:
        raise PolicyError("MEDIUM tasks require --allow-medium-risk")
    if task.risk is Risk.HIGH and not allow_high:
        raise PolicyError("HIGH tasks require --allow-high-risk and Codex ownership")
    if task.risk is Risk.CRITICAL:
        raise PolicyError("CRITICAL tasks cannot be delegated")
    for allowed in task.allowed_paths:
        if any(path_matches(allowed.rstrip("/") or allowed, rule) for rule in always_forbidden):
            raise PolicyError(f"Allowed path conflicts with a protected path: {allowed}")
        if task.risk is Risk.LOW and any(
            path_matches(allowed.rstrip("/"), prefix) for prefix in SENSITIVE_PREFIXES
        ):
            raise PolicyError(f"LOW task cannot modify sensitive path: {allowed}")
    if task.allow_network and task.risk is Risk.LOW:
        raise PolicyError("LOW tasks cannot request Internet access")


def validate_changed_paths(
    task: Task,
    paths: list[str],
    always_forbidden: tuple[str, ...],
) -> PolicyResult:
    violations: list[str] = []
    for path in paths:
        if any(path_matches(path, rule) for rule in always_forbidden):
            violations.append(f"protected path modified: {path}")
            continue
        if any(path_matches(path, rule) for rule in task.forbidden_paths):
            violations.append(f"task-forbidden path modified: {path}")
            continue
        if not any(path_matches(path, rule) for rule in task.allowed_paths):
            violations.append(f"outside allowed_paths: {path}")
    return PolicyResult(not violations, tuple(violations))


def scan_secrets(worktree: Path, paths: list[str]) -> PolicyResult:
    violations: list[str] = []
    for relative in paths:
        path = worktree / relative
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                violations.append(f"possible {name} in {relative}")
    return PolicyResult(not violations, tuple(violations))
