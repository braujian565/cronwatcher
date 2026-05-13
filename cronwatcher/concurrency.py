"""Concurrency limit enforcement for cron jobs.

Allows capping how many jobs from a given tag group (or globally) may
run simultaneously.  Limits are stored in a lightweight JSON file so
they survive process restarts.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_STORE = Path(os.environ.get("CRONWATCHER_DATA_DIR", "/var/lib/cronwatcher")) / "concurrency.json"


@dataclass
class ConcurrencyLimit:
    """A named concurrency slot bucket."""

    name: str
    max_running: int
    running: List[str] = field(default_factory=list)  # job names currently held

    def available(self) -> bool:
        return len(self.running) < self.max_running

    def acquire(self, job_name: str) -> bool:
        """Try to claim a slot.  Returns True on success."""
        if not self.available():
            return False
        if job_name not in self.running:
            self.running.append(job_name)
        return True

    def release(self, job_name: str) -> None:
        self.running = [j for j in self.running if j != job_name]

    def to_dict(self) -> dict:
        return {"name": self.name, "max_running": self.max_running, "running": list(self.running)}

    @classmethod
    def from_dict(cls, d: dict) -> "ConcurrencyLimit":
        return cls(name=d["name"], max_running=int(d["max_running"]), running=list(d.get("running", [])))


class ConcurrencyManager:
    """Persist and manage a collection of ConcurrencyLimit buckets."""

    def __init__(self, store_path: Path = DEFAULT_STORE) -> None:
        self._path = Path(store_path)
        self._limits: Dict[str, ConcurrencyLimit] = {}
        self._load()

    # ------------------------------------------------------------------
    def _load(self) -> None:
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text())
                self._limits = {k: ConcurrencyLimit.from_dict(v) for k, v in raw.items()}
            except (json.JSONDecodeError, KeyError):
                self._limits = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({k: v.to_dict() for k, v in self._limits.items()}, indent=2))

    # ------------------------------------------------------------------
    def set_limit(self, name: str, max_running: int) -> None:
        existing = self._limits.get(name)
        running = existing.running if existing else []
        self._limits[name] = ConcurrencyLimit(name=name, max_running=max_running, running=running)
        self._save()

    def get_limit(self, name: str) -> Optional[ConcurrencyLimit]:
        return self._limits.get(name)

    def acquire(self, name: str, job_name: str) -> bool:
        limit = self._limits.get(name)
        if limit is None:
            return True  # no limit configured → always allow
        ok = limit.acquire(job_name)
        if ok:
            self._save()
        return ok

    def release(self, name: str, job_name: str) -> None:
        limit = self._limits.get(name)
        if limit:
            limit.release(job_name)
            self._save()

    def all_limits(self) -> List[ConcurrencyLimit]:
        return list(self._limits.values())

    def remove(self, name: str) -> bool:
        if name in self._limits:
            del self._limits[name]
            self._save()
            return True
        return False
