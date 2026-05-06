"""Silence/suppress alerts for specific jobs during maintenance windows."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional


@dataclass
class SilenceEntry:
    job_name: str
    until: datetime
    reason: str = ""

    def is_active(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now(timezone.utc)
        return now < self.until

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "until": self.until.isoformat(),
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SilenceEntry":
        return cls(
            job_name=data["job_name"],
            until=datetime.fromisoformat(data["until"]),
            reason=data.get("reason", ""),
        )


class Silencer:
    """Persists and queries active silences for cron jobs."""

    def __init__(self, path: str = "/tmp/cronwatcher_silences.json") -> None:
        self._path = path
        self._silences: Dict[str, SilenceEntry] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        with open(self._path) as fh:
            raw = json.load(fh)
        self._silences = {
            k: SilenceEntry.from_dict(v) for k, v in raw.items()
        }

    def _save(self) -> None:
        with open(self._path, "w") as fh:
            json.dump(
                {k: v.to_dict() for k, v in self._silences.items()}, fh, indent=2
            )

    def silence(self, job_name: str, until: datetime, reason: str = "") -> None:
        """Add or update a silence for *job_name* until *until*."""
        self._silences[job_name] = SilenceEntry(
            job_name=job_name, until=until, reason=reason
        )
        self._save()

    def unsilence(self, job_name: str) -> bool:
        """Remove a silence. Returns True if one existed."""
        existed = job_name in self._silences
        self._silences.pop(job_name, None)
        if existed:
            self._save()
        return existed

    def is_silenced(self, job_name: str, now: Optional[datetime] = None) -> bool:
        """Return True if *job_name* has an active silence."""
        entry = self._silences.get(job_name)
        return entry is not None and entry.is_active(now)

    def active_silences(self, now: Optional[datetime] = None) -> list:
        """Return all currently active SilenceEntry objects."""
        return [e for e in self._silences.values() if e.is_active(now)]
