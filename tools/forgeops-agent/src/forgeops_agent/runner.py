from __future__ import annotations

import json
import queue
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path

from forgeops_agent.config import OrchestratorConfig
from forgeops_agent.errors import AgentError
from forgeops_agent.models import RunnerResult, Task
from forgeops_agent.system import safe_host_environment

ISOLATED_NETWORK = "forgeops-ai-isolated"
GATEWAY_CONTAINER = "forgeops-ai-ollama-gateway"


class LocalAgentRunner(ABC):
    @abstractmethod
    def doctor(self) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def run(
        self,
        task: Task,
        worktree: Path,
        prompt: Path,
        log_path: Path,
        model: str,
    ) -> RunnerResult:
        raise NotImplementedError

    @abstractmethod
    def stop(self, task_id: str) -> None:
        raise NotImplementedError


class AiderRunner(LocalAgentRunner):
    def __init__(self, config: OrchestratorConfig):
        self.config = config

    def doctor(self) -> dict[str, object]:
        docker = self._run(["docker", "version", "--format", "{{.Server.Version}}"], check=False)
        image = self._run(["docker", "image", "inspect", self.config.agent_image], check=False)
        return {
            "provider": "aider",
            "version": self.config.agent_version,
            "docker": docker.stdout.strip() if docker.returncode == 0 else None,
            "agent_image_ready": image.returncode == 0,
            "network_isolation": ISOLATED_NETWORK,
        }

    def ensure_runtime(self) -> None:
        self._ensure_image(
            self.config.agent_image,
            self.config.ai_root / "docker" / "Dockerfile.aider",
        )
        self._ensure_image(
            self.config.gateway_image,
            self.config.ai_root / "docker" / "Dockerfile.gateway",
        )
        if self._run(["docker", "network", "inspect", ISOLATED_NETWORK], check=False).returncode != 0:
            self._run(["docker", "network", "create", "--internal", ISOLATED_NETWORK])
        gateway = self._run(
            ["docker", "inspect", "-f", "{{.State.Running}}", GATEWAY_CONTAINER], check=False
        )
        if gateway.returncode != 0:
            self._run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--restart",
                    "unless-stopped",
                    "--name",
                    GATEWAY_CONTAINER,
                    "--network",
                    "bridge",
                    "--add-host",
                    "host.docker.internal:host-gateway",
                    self.config.gateway_image,
                ]
            )
        elif gateway.stdout.strip() != "true":
            self._run(["docker", "start", GATEWAY_CONTAINER])
        networks = self._run(
            ["docker", "inspect", "-f", "{{json .NetworkSettings.Networks}}", GATEWAY_CONTAINER]
        )
        if ISOLATED_NETWORK not in json.loads(networks.stdout):
            self._run(["docker", "network", "connect", ISOLATED_NETWORK, GATEWAY_CONTAINER])
        probe = self._run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                ISOLATED_NETWORK,
                "curlimages/curl:8.16.0",
                "-fsS",
                "--max-time",
                "10",
                f"http://{GATEWAY_CONTAINER}:11434/api/version",
            ],
            check=False,
        )
        if probe.returncode != 0:
            raise AgentError("The isolated agent network cannot reach local Ollama")

    def run(
        self,
        task: Task,
        worktree: Path,
        prompt: Path,
        log_path: Path,
        model: str,
    ) -> RunnerResult:
        self.ensure_runtime()
        container = self.container_name(task.id)
        network = "bridge" if task.allow_network else ISOLATED_NETWORK
        ollama_url = (
            "http://host.docker.internal:11434"
            if task.allow_network
            else f"http://{GATEWAY_CONTAINER}:11434"
        )
        editable_files = self._expand_task_files(worktree, task.allowed_paths, limit=50)
        read_only_files = [
            path
            for path in self._expand_task_files(worktree, task.context_files, limit=100)
            if path not in editable_files
        ]
        if not editable_files:
            raise AgentError("Aider tasks require at least one existing editable file")
        command = [
            "docker",
            "run",
            "--rm",
            "--init",
            "--name",
            container,
            "--network",
            network,
            "--cpus",
            str(self.config.container_cpus),
            "--memory",
            self.config.container_memory,
            "--pids-limit",
            "512",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,mode=1777,size=2g",
            "--tmpfs",
            "/home/agent:rw,nosuid,nodev,uid=10001,gid=10001,mode=0700,size=512m",
            "-v",
            f"{worktree}:/workspace:rw",
            "-v",
            f"{prompt}:/task/prompt.md:ro",
            "-w",
            "/workspace",
            "-e",
            "HOME=/home/agent",
            "-e",
            f"OLLAMA_API_BASE={ollama_url}",
            "-e",
            "AIDER_ANALYTICS=false",
            "-e",
            "NO_COLOR=1",
        ]
        if task.allow_network:
            command.extend(["--add-host", "host.docker.internal:host-gateway"])
        command.extend(
            [
                self.config.agent_image,
                "aider",
                "--model",
                f"ollama_chat/{model}",
                "--weak-model",
                f"ollama_chat/{model}",
                "--message-file",
                "/task/prompt.md",
                "--yes-always",
                "--no-git",
                "--no-gitignore",
                "--no-auto-commits",
                "--no-dirty-commits",
                "--no-suggest-shell-commands",
                "--no-check-update",
                "--no-analytics",
                "--no-show-model-warnings",
                "--no-pretty",
                "--no-stream",
                "--no-detect-urls",
                "--edit-format",
                "whole",
                "--input-history-file",
                "/home/agent/.aider.input.history",
                "--chat-history-file",
                "/home/agent/.aider.chat.history.md",
            ]
        )
        for path in editable_files:
            command.extend(["--file", path])
        for path in read_only_files:
            command.extend(["--read", path])
        return self._run_monitored(task, command, log_path)

    @staticmethod
    def _expand_task_files(
        worktree: Path,
        paths: tuple[str, ...],
        *,
        limit: int,
    ) -> list[str]:
        files: list[str] = []
        for relative in paths:
            candidate = worktree / relative
            if candidate.is_file():
                files.append(relative)
                continue
            if candidate.is_dir():
                files.extend(
                    path.relative_to(worktree).as_posix()
                    for path in candidate.rglob("*")
                    if path.is_file() and ".git" not in path.parts
                )
            if len(files) > limit:
                raise AgentError(
                    f"Task context expands to more than {limit} files; narrow its paths"
                )
        return sorted(set(files))

    def stop(self, task_id: str) -> None:
        self._run(
            ["docker", "stop", "--time", "10", self.container_name(task_id)], check=False
        )

    @staticmethod
    def container_name(task_id: str) -> str:
        return f"forgeops-agent-{task_id.lower()}"

    def _ensure_image(self, image: str, dockerfile: Path) -> None:
        if self._run(["docker", "image", "inspect", image], check=False).returncode == 0:
            return
        self._run(
            [
                "docker",
                "build",
                "--build-arg",
                f"AIDER_VERSION={self.config.agent_version}",
                "-t",
                image,
                "-f",
                str(dockerfile),
                str(dockerfile.parent),
            ],
            timeout=1800,
        )

    def _run_monitored(
        self,
        task: Task,
        command: list[str],
        log_path: Path,
    ) -> RunnerResult:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        process = subprocess.Popen(
            command,
            cwd=self.config.repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=safe_host_environment(),
        )
        lines: queue.Queue[str | None] = queue.Queue()

        def read_output() -> None:
            assert process.stdout is not None
            for line in process.stdout:
                lines.put(line)
            lines.put(None)

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        stopped = False
        timed_out = False
        output: list[str] = []
        timeout_seconds = task.timeout_minutes * 60
        with log_path.open("w", encoding="utf-8") as log:
            while process.poll() is None:
                self._drain(lines, log, output)
                if (self.config.ai_root / "STOP").exists():
                    stopped = True
                    self.stop(task.id)
                    break
                if time.monotonic() - started >= timeout_seconds:
                    timed_out = True
                    self.stop(task.id)
                    break
                time.sleep(1)
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
            reader.join(timeout=5)
            self._drain(lines, log, output)
        self._truncate_log(log_path)
        duration = time.monotonic() - started
        summary = "".join(output[-25:])[-4000:].strip() or "No agent output"
        return RunnerResult(
            return_code=process.returncode or 0,
            timed_out=timed_out,
            stopped=stopped,
            duration_seconds=duration,
            log_path=str(log_path),
            summary=summary,
        )

    @staticmethod
    def _drain(lines: queue.Queue[str | None], log, output: list[str]) -> None:
        while True:
            try:
                line = lines.get_nowait()
            except queue.Empty:
                return
            if line is None:
                return
            log.write(line)
            log.flush()
            output.append(line)
            if len(output) > 200:
                del output[:100]

    def _truncate_log(self, path: Path) -> None:
        if path.stat().st_size <= self.config.log_max_bytes:
            return
        with path.open("rb") as source:
            source.seek(-self.config.log_max_bytes, 2)
            content = source.read()
        path.write_bytes(b"[earlier output truncated]\n" + content)

    @staticmethod
    def _run(
        command: list[str],
        check: bool = True,
        timeout: int = 120,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout,
            env=safe_host_environment(),
        )
        if check and result.returncode != 0:
            detail = "\n".join((result.stdout + result.stderr).splitlines()[-20:])
            raise AgentError(f"Command failed: {' '.join(command[:4])}\n{detail}")
        return result
