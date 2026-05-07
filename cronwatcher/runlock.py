"""Run-lock mechanism to prevent overlapping cron job executions."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class LockEntry:
    job_name: str
    pid: int
    started_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "pid": self.pid,
            "started_at": self.started_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LockEntry":
        return cls(
            job_name=data["job_name"],
            pid=data["pid"],
            started_at=data.get("started_at", 0.0),
        )

    def is_stale(self) -> bool:
        """Return True if the owning process is no longer running."""
        try:
            os.kill(self.pid, 0)
            return False
        except (ProcessLookupError, PermissionError):
            return True


class RunLock:
    """File-backed lock store; one lock file per job."""

    def __init__(self, lock_dir: Path) -> None:
        self.lock_dir = Path(lock_dir)
        self.lock_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        safe = job_name.replace("/", "_").replace(" ", "_")
        return self.lock_dir / f"{safe}.lock"

    def acquire(self, job_name: str) -> bool:
        """Try to acquire a lock. Returns True on success, False if already locked."""
        path = self._path(job_name)
        if path.exists():
            try:
                entry = LockEntry.from_dict(json.loads(path.read_text()))
                if not entry.is_stale():
                    return False
                # stale lock — remove it
                path.unlink(missing_ok=True)
            except (json.JSONDecodeError, KeyError):
                path.unlink(missing_ok=True)

        entry = LockEntry(job_name=job_name, pid=os.getpid())
        path.write_text(json.dumps(entry.to_dict()))
        return True

    def release(self, job_name: str) -> None:
        self._path(job_name).unlink(missing_ok=True)

    def is_locked(self, job_name: str) -> bool:
        path = self._path(job_name)
        if not path.exists():
            return False
        try:
            entry = LockEntry.from_dict(json.loads(path.read_text()))
            if entry.is_stale():
                path.unlink(missing_ok=True)
                return False
            return True
        except (json.JSONDecodeError, KeyError):
            path.unlink(missing_ok=True)
            return False

    def current_entry(self, job_name: str) -> Optional[LockEntry]:
        path = self._path(job_name)
        if not path.exists():
            return None
        try:
            return LockEntry.from_dict(json.loads(path.read_text()))
        except (json.JSONDecodeError, KeyError):
            return None
