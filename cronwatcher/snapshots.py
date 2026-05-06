"""Point-in-time snapshots of job state for trend analysis and diffing."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class JobSnapshot:
    """Captures the state of a single job at a point in time."""

    job_name: str
    captured_at: str  # ISO-8601
    last_exit_code: Optional[int]
    consecutive_failures: int
    last_run_at: Optional[str]

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "captured_at": self.captured_at,
            "last_exit_code": self.last_exit_code,
            "consecutive_failures": self.consecutive_failures,
            "last_run_at": self.last_run_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobSnapshot":
        return cls(
            job_name=data["job_name"],
            captured_at=data["captured_at"],
            last_exit_code=data.get("last_exit_code"),
            consecutive_failures=data.get("consecutive_failures", 0),
            last_run_at=data.get("last_run_at"),
        )


@dataclass
class Snapshot:
    """A full snapshot of all tracked jobs at a given moment."""

    taken_at: str
    jobs: Dict[str, JobSnapshot] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "taken_at": self.taken_at,
            "jobs": {name: snap.to_dict() for name, snap in self.jobs.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Snapshot":
        snap = cls(taken_at=data["taken_at"])
        for name, job_data in data.get("jobs", {}).items():
            snap.jobs[name] = JobSnapshot.from_dict(job_data)
        return snap


def take_snapshot(store) -> Snapshot:
    """Create a Snapshot from the current JobStore state."""
    now = datetime.now(timezone.utc).isoformat()
    snapshot = Snapshot(taken_at=now)
    for name, record in store._data.items():
        snapshot.jobs[name] = JobSnapshot(
            job_name=name,
            captured_at=now,
            last_exit_code=record.last_exit_code,
            consecutive_failures=record.consecutive_failures,
            last_run_at=record.last_run_at,
        )
    return snapshot


def save_snapshot(snapshot: Snapshot, path: str) -> None:
    """Persist a snapshot to a JSON file."""
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w") as fh:
        json.dump(snapshot.to_dict(), fh, indent=2)


def load_snapshot(path: str) -> Optional[Snapshot]:
    """Load a snapshot from disk; returns None if file is missing."""
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return Snapshot.from_dict(json.load(fh))


def diff_snapshots(old: Snapshot, new: Snapshot) -> List[str]:
    """Return human-readable lines describing changes between two snapshots."""
    lines: List[str] = []
    all_names = set(old.jobs) | set(new.jobs)
    for name in sorted(all_names):
        if name not in old.jobs:
            lines.append(f"{name}: new job appeared")
            continue
        if name not in new.jobs:
            lines.append(f"{name}: job removed")
            continue
        o, n = old.jobs[name], new.jobs[name]
        if o.consecutive_failures != n.consecutive_failures:
            lines.append(
                f"{name}: consecutive_failures {o.consecutive_failures} -> {n.consecutive_failures}"
            )
        if o.last_exit_code != n.last_exit_code:
            lines.append(f"{name}: exit_code {o.last_exit_code} -> {n.last_exit_code}")
    return lines
