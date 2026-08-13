from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import psutil

from forgeops_agent.errors import LockError


class FileLock:
    def __init__(self, path: Path):
        self.path = path
        self.acquired = False

    def acquire(self) -> FileLock:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {"pid": os.getpid(), "started_at": datetime.now(UTC).isoformat()}, indent=2
        )
        for _ in range(2):
            try:
                descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    handle.write(payload)
                self.acquired = True
                return self
            except FileExistsError as exc:
                if self._clear_stale_lock():
                    continue
                raise LockError(f"Active lock: {self.path}") from exc
        raise LockError(f"Could not acquire lock: {self.path}")

    def _clear_stale_lock(self) -> bool:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            pid = int(data["pid"])
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            self.path.unlink(missing_ok=True)
            return True
        if pid == os.getpid() or psutil.pid_exists(pid):
            return False
        self.path.unlink(missing_ok=True)
        return True

    def release(self) -> None:
        if self.acquired:
            self.path.unlink(missing_ok=True)
            self.acquired = False

    def __enter__(self) -> FileLock:
        return self.acquire()

    def __exit__(self, *_args) -> None:
        self.release()

