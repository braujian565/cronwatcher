"""Checkpoint support: persist and retrieve the last successful run timestamp per job."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class CheckpointEntry:
    job_name: str
    last_success: datetime

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "last_success": self.last_success.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CheckpointEntry":
        return cls(
            job_name=data["job_name"],
            last_success=datetime.fromisoformat(data["last_success"]),
        )

    def age_seconds(self, now: Optional[datetime] = None) -> float:
        """Return how many seconds ago the last success occurred."""
        if now is None:
            now = datetime.now(timezone.utc)
        last = self.last_success
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return (now - last).total_seconds()


class Checkpointer:
    """Stores per-job checkpoint files in a directory."""

    def __init__(self, directory: str) -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        safe = job_name.replace(os.sep, "_").replace(" ", "_")
        return self._dir / f"{safe}.checkpoint.json"

    def save(self, job_name: str, ts: Optional[datetime] = None) -> CheckpointEntry:
        """Persist a successful-run timestamp (defaults to now)."""
        if ts is None:
            ts = datetime.now(timezone.utc)
        entry = CheckpointEntry(job_name=job_name, last_success=ts)
        self._path(job_name).write_text(json.dumps(entry.to_dict()), encoding="utf-8")
        return entry

    def load(self, job_name: str) -> Optional[CheckpointEntry]:
        """Return the checkpoint for *job_name*, or None if it does not exist."""
        p = self._path(job_name)
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        return CheckpointEntry.from_dict(data)

    def delete(self, job_name: str) -> bool:
        """Remove the checkpoint file. Returns True if a file was removed."""
        p = self._path(job_name)
        if p.exists():
            p.unlink()
            return True
        return False

    def all_entries(self) -> list[CheckpointEntry]:
        """Return all stored checkpoint entries, sorted by job name."""
        entries = []
        for p in sorted(self._dir.glob("*.checkpoint.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                entries.append(CheckpointEntry.from_dict(data))
            except (KeyError, ValueError):
                continue
        return entries
