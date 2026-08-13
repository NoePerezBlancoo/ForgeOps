from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

import psutil

SAFE_ENVIRONMENT_KEYS = (
    "ALLUSERSPROFILE",
    "APPDATA",
    "COMSPEC",
    "HOME",
    "HOMEDRIVE",
    "HOMEPATH",
    "LOCALAPPDATA",
    "NUMBER_OF_PROCESSORS",
    "OS",
    "PATH",
    "PATHEXT",
    "PROGRAMDATA",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
    "SYSTEMDRIVE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "USERPROFILE",
    "WINDIR",
)


def safe_host_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    environment = {key: os.environ[key] for key in SAFE_ENVIRONMENT_KEYS if key in os.environ}
    environment.update(
        {
            "CI": "true",
            "GIT_TERMINAL_PROMPT": "0",
            "PYTHONUTF8": "1",
            "NO_COLOR": "1",
        }
    )
    if extra:
        environment.update(extra)
    return environment


def executable(name: str) -> str | None:
    return shutil.which(name)


def command_version(command: list[str]) -> str | None:
    resolved = list(command)
    if os.name == "nt" and resolved[0].lower() == "npm":
        resolved[0] = "npm.cmd"
    try:
        result = subprocess.run(
            resolved,
            capture_output=True,
            text=True,
            timeout=10,
            env=safe_host_environment(),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    raw_output = (result.stdout or result.stderr).replace("\x00", "")
    output = raw_output.strip().splitlines()
    return output[0] if output else None


def ollama_version(base_url: str) -> str | None:
    try:
        with urlopen(f"{base_url.rstrip('/')}/api/version", timeout=5) as response:
            return json.load(response).get("version")
    except (OSError, URLError, json.JSONDecodeError):
        return None


def gpu_metrics() -> dict[str, Any] | None:
    if not executable("nvidia-smi"):
        return None
    query = "name,driver_version,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu"
    result = subprocess.run(
        ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
        env=safe_host_environment(),
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    parts = [part.strip() for part in result.stdout.splitlines()[0].split(",")]
    if len(parts) != 7:
        return None
    return {
        "name": parts[0],
        "driver": parts[1],
        "memory_total_mb": int(parts[2]),
        "memory_used_mb": int(parts[3]),
        "memory_free_mb": int(parts[4]),
        "temperature_c": int(parts[5]),
        "utilization_percent": int(parts[6]),
    }


def resource_snapshot(path: Path) -> dict[str, Any]:
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(path.anchor or str(path))
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "memory_total_gb": round(memory.total / 1024**3, 2),
        "memory_available_gb": round(memory.available / 1024**3, 2),
        "disk_free_gb": round(disk.free / 1024**3, 2),
        "gpu": gpu_metrics(),
    }


def resource_violations(snapshot: dict[str, Any], config) -> list[str]:
    violations: list[str] = []
    if snapshot["cpu_percent"] > config.max_cpu_percent:
        violations.append(f"CPU at {snapshot['cpu_percent']}%")
    if snapshot["memory_available_gb"] < config.min_free_memory_gb:
        violations.append(f"only {snapshot['memory_available_gb']} GB RAM available")
    if snapshot["disk_free_gb"] < config.min_free_disk_gb:
        violations.append(f"only {snapshot['disk_free_gb']} GB disk free")
    gpu = snapshot.get("gpu")
    if gpu and gpu["temperature_c"] > config.max_gpu_temperature_c:
        violations.append(f"GPU at {gpu['temperature_c']} C")
    return violations
