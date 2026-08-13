from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from forgeops_agent.errors import ConfigurationError


def find_repo_root(start: Path | None = None) -> Path:
    cwd = (start or Path.cwd()).resolve()
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ConfigurationError("forgeops-agent must run inside a Git repository")
    return Path(result.stdout.strip()).resolve()


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigurationError(f"Missing configuration file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ConfigurationError(f"Expected a YAML mapping in {path}")
    return data


@dataclass(frozen=True)
class OrchestratorConfig:
    repo_root: Path
    ai_root: Path
    worktrees_root: Path
    agent_provider: str
    agent_image: str
    gateway_image: str
    agent_version: str
    model_catalog: dict[str, dict[str, Any]]
    routing_policy: dict[str, dict[str, Any]]
    fallback_statuses: tuple[str, ...]
    max_model_attempts: int
    ollama_url: str
    context_tokens: int
    max_parallel_tasks: int
    max_iterations: int
    default_timeout_minutes: int
    idle_poll_seconds: int
    protected_branches: tuple[str, ...]
    protected_path_prefixes: tuple[str, ...]
    automatic_risks: tuple[str, ...]
    max_cpu_percent: float
    min_free_memory_gb: float
    min_free_disk_gb: float
    max_gpu_temperature_c: int
    container_cpus: float
    container_memory: str
    log_max_bytes: int

    @classmethod
    def load(cls, repo_root: Path | None = None) -> OrchestratorConfig:
        root = find_repo_root(repo_root)
        ai_root = root / ".ai"
        data = load_yaml(ai_root / "config" / "orchestrator.yaml")
        permissions = load_yaml(ai_root / "config" / "permissions.yaml")
        models = load_yaml(ai_root / "config" / "models.yaml")
        try:
            worktrees_value = data["git"]["worktrees_root"]
            worktrees = (
                (root / worktrees_value).resolve()
                if not Path(worktrees_value).is_absolute()
                else Path(worktrees_value).resolve()
            )
            return cls(
                repo_root=root,
                ai_root=ai_root,
                worktrees_root=worktrees,
                agent_provider=data["agent"]["provider"],
                agent_image=data["agent"]["image"],
                gateway_image=data["agent"]["gateway_image"],
                agent_version=str(data["agent"]["version"]),
                model_catalog={
                    str(alias).lower(): dict(definition)
                    for alias, definition in models["models"].items()
                },
                routing_policy={
                    str(risk).upper(): dict(policy)
                    for risk, policy in models["routing"].items()
                },
                fallback_statuses=tuple(models["fallback"]["retryable_statuses"]),
                max_model_attempts=int(models["limits"]["max_model_attempts"]),
                ollama_url=models["ollama"]["host_url"],
                context_tokens=int(models["ollama"]["context_tokens"]),
                max_parallel_tasks=int(data["execution"]["max_parallel_tasks"]),
                max_iterations=int(data["execution"]["max_iterations"]),
                default_timeout_minutes=int(data["execution"]["default_timeout_minutes"]),
                idle_poll_seconds=int(data["execution"]["idle_poll_seconds"]),
                protected_branches=tuple(data["git"]["protected_branches"]),
                protected_path_prefixes=tuple(permissions["paths"]["always_forbidden"]),
                automatic_risks=tuple(data["security"]["automatic_risks"]),
                max_cpu_percent=float(data["resources"]["max_cpu_percent"]),
                min_free_memory_gb=float(data["resources"]["min_free_memory_gb"]),
                min_free_disk_gb=float(data["resources"]["min_free_disk_gb"]),
                max_gpu_temperature_c=int(data["resources"]["max_gpu_temperature_c"]),
                container_cpus=float(data["resources"]["container_cpus"]),
                container_memory=str(data["resources"]["container_memory"]),
                log_max_bytes=int(data["reports"]["log_max_bytes"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ConfigurationError(f"Invalid orchestrator configuration: {exc}") from exc

    @property
    def primary_model(self) -> str:
        alias = str(self.routing_policy["LOW"]["primary"]).lower()
        return str(self.model_catalog[alias]["model"])

    @property
    def fallback_model(self) -> str | None:
        alias = self.routing_policy["LOW"].get("fallback")
        return str(self.model_catalog[str(alias).lower()]["model"]) if alias else None
