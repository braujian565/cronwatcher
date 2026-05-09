"""Cooldown tracker: prevents a job from being re-run too soon after a recent execution."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class CooldownEntry:
    job_name: str
    last_run_ts: float  # unix timestamp
    cooldown_seconds: int

    def is_cooling_down(self, now: Optional[float] = None) -> bool:
        """Return True if the job is still within its cooldown window."""
        now = now if now is not None else time.time()
        return (now - self.last_run_ts) < self.cooldown_seconds

    def seconds_remaining(self, now: Optional[float] = None) -> float:
        now = now if now is not None else time.time()
        remaining = self.cooldown_seconds - (now - self.last_run_ts)
        return max(0.0, remaining)

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "last_run_ts": self.last_run_ts,
            "cooldown_seconds": self.cooldown_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CooldownEntry":
        return cls(
            job_name=data["job_name"],
            last_run_ts=float(data.get("last_run_ts", 0.0)),
            cooldown_seconds=int(data.get("cooldown_seconds", 0)),
        )


class CooldownTracker:
    def __init__(self, store_path: Path) -> None:
        self._path = store_path
        self._entries: Dict[str, CooldownEntry] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text())
                self._entries = {
                    k: CooldownEntry.from_dict(v) for k, v in raw.items()
                }
            except (json.JSONDecodeError, KeyError):
                self._entries = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps({k: v.to_dict() for k, v in self._entries.items()}, indent=2)
        )

    def record_run(self, job_name: str, cooldown_seconds: int, now: Optional[float] = None) -> None:
        """Mark a job as just-run, starting its cooldown window."""
        ts = now if now is not None else time.time()
        self._entries[job_name] = CooldownEntry(
            job_name=job_name,
            last_run_ts=ts,
            cooldown_seconds=cooldown_seconds,
        )
        self._save()

    def is_cooling_down(self, job_name: str, now: Optional[float] = None) -> bool:
        entry = self._entries.get(job_name)
        if entry is None:
            return False
        return entry.is_cooling_down(now=now)

    def seconds_remaining(self, job_name: str, now: Optional[float] = None) -> float:
        entry = self._entries.get(job_name)
        if entry is None:
            return 0.0
        return entry.seconds_remaining(now=now)

    def all_entries(self) -> list:
        return list(self._entries.values())

    def reset(self, job_name: str) -> bool:
        if job_name in self._entries:
            del self._entries[job_name]
            self._save()
            return True
        return False
