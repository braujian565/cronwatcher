"""Audit log: append-only record of every job execution event."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class AuditEntry:
    job_name: str
    timestamp: str          # ISO-8601 UTC
    exit_code: int
    duration_seconds: float
    retries: int = 0
    stderr_snippet: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "timestamp": self.timestamp,
            "exit_code": self.exit_code,
            "duration_seconds": self.duration_seconds,
            "retries": self.retries,
            "stderr_snippet": self.stderr_snippet,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AuditEntry":
        return cls(
            job_name=d["job_name"],
            timestamp=d["timestamp"],
            exit_code=d["exit_code"],
            duration_seconds=d["duration_seconds"],
            retries=d.get("retries", 0),
            stderr_snippet=d.get("stderr_snippet"),
            tags=d.get("tags", []),
        )


class AuditLog:
    """Append-only JSONL audit log stored on disk."""

    def __init__(self, path: str) -> None:
        self.path = path

    def append(self, entry: AuditEntry) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.to_dict()) + "\n")

    def read_all(self) -> List[AuditEntry]:
        if not os.path.exists(self.path):
            return []
        entries: List[AuditEntry] = []
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    entries.append(AuditEntry.from_dict(json.loads(line)))
        return entries

    def read_for_job(self, job_name: str) -> List[AuditEntry]:
        return [e for e in self.read_all() if e.job_name == job_name]


def make_entry(
    job_name: str,
    exit_code: int,
    duration_seconds: float,
    retries: int = 0,
    stderr: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> AuditEntry:
    """Convenience factory that stamps the current UTC time."""
    snippet = (stderr or "")[:200] or None
    return AuditEntry(
        job_name=job_name,
        timestamp=datetime.now(timezone.utc).isoformat(),
        exit_code=exit_code,
        duration_seconds=round(duration_seconds, 3),
        retries=retries,
        stderr_snippet=snippet,
        tags=tags or [],
    )
