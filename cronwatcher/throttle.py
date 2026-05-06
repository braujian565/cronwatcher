"""Alert throttling: suppress repeated alerts for the same job within a cooldown window."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class ThrottleEntry:
    job_name: str
    last_alerted_at: float  # unix timestamp
    alert_count: int = 1

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "last_alerted_at": self.last_alerted_at,
            "alert_count": self.alert_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ThrottleEntry":
        return cls(
            job_name=data["job_name"],
            last_alerted_at=float(data["last_alerted_at"]),
            alert_count=int(data.get("alert_count", 1)),
        )


class Throttler:
    """Persists per-job alert timestamps and enforces a cooldown period."""

    def __init__(self, state_path: Path, cooldown_seconds: int = 3600) -> None:
        self.state_path = state_path
        self.cooldown_seconds = cooldown_seconds
        self._entries: Dict[str, ThrottleEntry] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_suppressed(self, job_name: str, now: Optional[float] = None) -> bool:
        """Return True if an alert for *job_name* should be suppressed."""
        now = now if now is not None else time.time()
        entry = self._entries.get(job_name)
        if entry is None:
            return False
        return (now - entry.last_alerted_at) < self.cooldown_seconds

    def record_alert(self, job_name: str, now: Optional[float] = None) -> None:
        """Record that an alert was sent for *job_name* right now."""
        now = now if now is not None else time.time()
        entry = self._entries.get(job_name)
        if entry is None:
            self._entries[job_name] = ThrottleEntry(job_name=job_name, last_alerted_at=now)
        else:
            entry.last_alerted_at = now
            entry.alert_count += 1
        self._save()

    def reset(self, job_name: str) -> None:
        """Clear throttle state for *job_name* (e.g. after a successful run)."""
        self._entries.pop(job_name, None)
        self._save()

    def get_entry(self, job_name: str) -> Optional[ThrottleEntry]:
        return self._entries.get(job_name)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self.state_path.exists():
            return
        try:
            raw = json.loads(self.state_path.read_text())
            self._entries = {
                k: ThrottleEntry.from_dict(v) for k, v in raw.items()
            }
        except (json.JSONDecodeError, KeyError):
            self._entries = {}

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps({k: v.to_dict() for k, v in self._entries.items()}, indent=2)
        )
