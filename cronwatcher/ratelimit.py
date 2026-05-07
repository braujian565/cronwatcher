"""Per-job alert rate limiting using a sliding window counter."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class RateLimitEntry:
    job_name: str
    timestamps: List[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"job_name": self.job_name, "timestamps": self.timestamps}

    @classmethod
    def from_dict(cls, data: dict) -> "RateLimitEntry":
        return cls(
            job_name=data["job_name"],
            timestamps=data.get("timestamps", []),
        )

    def prune(self, window_seconds: float, now: float | None = None) -> None:
        """Remove timestamps older than the sliding window."""
        now = now or time.time()
        cutoff = now - window_seconds
        self.timestamps = [t for t in self.timestamps if t >= cutoff]

    def count_in_window(self, window_seconds: float, now: float | None = None) -> int:
        now = now or time.time()
        self.prune(window_seconds, now)
        return len(self.timestamps)

    def record(self, now: float | None = None) -> None:
        self.timestamps.append(now or time.time())


class RateLimiter:
    def __init__(self, store_path: Path, window_seconds: float = 3600.0, max_alerts: int = 5):
        self.store_path = store_path
        self.window_seconds = window_seconds
        self.max_alerts = max_alerts
        self._data: Dict[str, RateLimitEntry] = {}
        self._load()

    def _load(self) -> None:
        if self.store_path.exists():
            raw = json.loads(self.store_path.read_text())
            self._data = {k: RateLimitEntry.from_dict(v) for k, v in raw.items()}

    def _save(self) -> None:
        self.store_path.write_text(json.dumps({k: v.to_dict() for k, v in self._data.items()}, indent=2))

    def _entry(self, job_name: str) -> RateLimitEntry:
        if job_name not in self._data:
            self._data[job_name] = RateLimitEntry(job_name=job_name)
        return self._data[job_name]

    def is_limited(self, job_name: str, now: float | None = None) -> bool:
        """Return True if the job has exceeded the alert rate limit."""
        entry = self._entry(job_name)
        return entry.count_in_window(self.window_seconds, now) >= self.max_alerts

    def record_alert(self, job_name: str, now: float | None = None) -> None:
        """Record that an alert was sent for this job."""
        entry = self._entry(job_name)
        entry.record(now)
        self._save()

    def reset(self, job_name: str) -> None:
        """Clear rate limit history for a job."""
        if job_name in self._data:
            self._data[job_name].timestamps = []
            self._save()

    def all_entries(self) -> List[RateLimitEntry]:
        return list(self._data.values())
