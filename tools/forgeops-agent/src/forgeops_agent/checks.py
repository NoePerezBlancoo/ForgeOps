from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path

from forgeops_agent.models import CheckResult, Task
from forgeops_agent.system import safe_host_environment

SAFE_TARGET = re.compile(r"^[A-Za-z0-9_./-]+(?:::[A-Za-z0-9_./-]+)?$")


class CheckRunner:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self._backend_images: dict[str, str] = {}

    def resolve(self, task: Task, changed_files: list[str]) -> list[str]:
        requested = list(task.required_checks)
        if requested:
            return requested
        checks: list[str] = []
        if any(path.startswith("backend/") for path in changed_files):
            checks.extend(["backend-ruff", "backend-pytest"])
        if any(path.startswith("frontend/") for path in changed_files):
            checks.append("frontend-quality")
        return checks

    def run_all(
        self,
        task: Task,
        worktree: Path,
        changed_files: list[str],
    ) -> list[CheckResult]:
        results: list[CheckResult] = []
        for name in self.resolve(task, changed_files):
            result = self.run(name, task.id, worktree)
            results.append(result)
            if not result.passed:
                break
        return results

    def run(self, name: str, task_id: str, worktree: Path) -> CheckResult:
        started = time.monotonic()
        try:
            command = self._command(name, task_id, worktree)
        except ValueError as exc:
            return CheckResult(name, False, 2, 0, str(exc))
        result = subprocess.run(
            command,
            cwd=worktree,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800,
            check=False,
            env=safe_host_environment(),
        )
        duration = time.monotonic() - started
        output = (result.stdout + "\n" + result.stderr).strip()
        summary = "\n".join(output.splitlines()[-12:])[-3000:] or "No output"
        return CheckResult(name, result.returncode == 0, result.returncode, duration, summary)

    def _command(self, name: str, task_id: str, worktree: Path) -> list[str]:
        if name in {"backend-ruff", "ruff"}:
            image = self._backend_image(task_id, worktree)
            return [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--entrypoint",
                "ruff",
                image,
                "check",
                "app",
                "scripts",
                "tests",
                "alembic",
            ]
        if name == "backend-pytest" or name == "pytest":
            image = self._backend_image(task_id, worktree)
            return ["docker", "run", "--rm", "--network", "none", "--entrypoint", "pytest", image, "-q"]
        if name.startswith("pytest:"):
            target = name.split(":", 1)[1]
            if not SAFE_TARGET.fullmatch(target) or not target.startswith("tests/"):
                raise ValueError(f"Unsafe pytest target: {target}")
            image = self._backend_image(task_id, worktree)
            return [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "--entrypoint",
                "pytest",
                image,
                "-q",
                target,
            ]
        if name == "frontend-quality":
            script = "npm ci --ignore-scripts && npm run lint && npm run typecheck && npm test && npm run build"
            return [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{worktree / 'frontend'}:/app",
                "-w",
                "/app",
                "node:22-alpine",
                "sh",
                "-lc",
                script,
            ]
        if name == "docker-config":
            return ["docker", "compose", "config", "--quiet"]
        raise ValueError(f"Unknown required check: {name}")

    def _backend_image(self, task_id: str, worktree: Path) -> str:
        cached = self._backend_images.get(task_id)
        if cached:
            return cached
        image = f"forgeops-ai-check:{task_id.lower()}"
        result = subprocess.run(
            [
                "docker",
                "build",
                "--build-arg",
                "INSTALL_DEV=true",
                "-t",
                image,
                "-f",
                str(worktree / "backend" / "Dockerfile"),
                str(worktree / "backend"),
            ],
            cwd=worktree,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800,
            check=False,
            env=safe_host_environment(),
        )
        if result.returncode != 0:
            detail = "\n".join((result.stdout + result.stderr).splitlines()[-20:])
            raise ValueError(f"Backend check image failed to build:\n{detail}")
        self._backend_images[task_id] = image
        return image

