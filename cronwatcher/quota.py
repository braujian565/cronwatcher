"""Per-job run quota enforcement: limit how many times a job may run in a time window."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_QUOTA_FILE = "/var/lib/cronwatcher/quotas.json"


@dataclass
class QuotaEntry:
    job_name: str
    max_runs: int
    window_seconds: int
    timestamps: List[float] = field(default_factory=list)

    def prune(self, now: Optional[float] = None) -> None:
        """Remove timestamps older than the window."""
        now = now or time.time()
        cutoff = now - self.window_seconds
        self.timestamps = [t for t in self.timestamps if t >= cutoff]

    def count_in_window(self, now: Optional[float] = None) -> int:
        self.prune(now)
        return len(self.timestamps)

    def is_exceeded(self, now: Optional[float] = None) -> bool:
        return self.count_in_window(now) >= self.max_runs

    def record_run(self, now: Optional[float] = None) -> None:
        now = now or time.time()
        self.prune(now)
        self.timestamps.append(now)

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "max_runs": self.max_runs,
            "window_seconds": self.window_seconds,
            "timestamps": self.timestamps,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QuotaEntry":
        return cls(
            job_name=data["job_name"],
            max_runs=data["max_runs"],
            window_seconds=data["window_seconds"],
            timestamps=data.get("timestamps", []),
        )


class QuotaManager:
    def __init__(self, store_path: str = DEFAULT_QUOTA_FILE) -> None:
        self._path = Path(store_path)
        self._entries: Dict[str, QuotaEntry] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            raw = json.loads(self._path.read_text())
            self._entries = {
                k: QuotaEntry.from_dict(v) for k, v in raw.items()
            }

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps({k: v.to_dict() for k, v in self._entries.items()}, indent=2)
        )

    def set_quota(self, job_name: str, max_runs: int, window_seconds: int) -> None:
        existing = self._entries.get(job_name)
        if existing:
            existing.max_runs = max_runs
            existing.window_seconds = window_seconds
        else:
            self._entries[job_name] = QuotaEntry(job_name, max_runs, window_seconds)
        self._save()

    def get_entry(self, job_name: str) -> Optional[QuotaEntry]:
        return self._entries.get(job_name)

    def is_exceeded(self, job_name: str, now: Optional[float] = None) -> bool:
        entry = self._entries.get(job_name)
        return entry.is_exceeded(now) if entry else False

    def record_run(self, job_name: str, now: Optional[float] = None) -> None:
        entry = self._entries.get(job_name)
        if entry:
            entry.record_run(now)
            self._save()

    def remove(self, job_name: str) -> bool:
        if job_name in self._entries:
            del self._entries[job_name]
            self._save()
            return True
        return False

    def all_entries(self) -> List[QuotaEntry]:
        return list(self._entries.values())
