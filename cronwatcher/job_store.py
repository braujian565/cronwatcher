"""Persistent storage for cron job execution records."""

import json
import os
import time
from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class JobRecord:
    job_name: str
    last_success: Optional[float] = None
    last_failure: Optional[float] = None
    last_exit_code: Optional[int] = None
    consecutive_failures: int = 0
    total_runs: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "JobRecord":
        return cls(**data)


class JobStore:
    """Manages persistent job execution state using a JSON file."""

    def __init__(self, store_path: str):
        self.store_path = store_path
        self._records: dict[str, JobRecord] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.store_path):
            return
        with open(self.store_path, "r") as f:
            raw = json.load(f)
        for name, data in raw.items():
            self._records[name] = JobRecord.from_dict(data)

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
        with open(self.store_path, "w") as f:
            json.dump(
                {name: rec.to_dict() for name, rec in self._records.items()},
                f,
                indent=2,
            )

    def get(self, job_name: str) -> JobRecord:
        if job_name not in self._records:
            self._records[job_name] = JobRecord(job_name=job_name)
        return self._records[job_name]

    def record_success(self, job_name: str) -> JobRecord:
        rec = self.get(job_name)
        rec.last_success = time.time()
        rec.consecutive_failures = 0
        rec.last_exit_code = 0
        rec.total_runs += 1
        self._save()
        return rec

    def record_failure(self, job_name: str, exit_code: int) -> JobRecord:
        rec = self.get(job_name)
        rec.last_failure = time.time()
        rec.consecutive_failures += 1
        rec.last_exit_code = exit_code
        rec.total_runs += 1
        self._save()
        return rec

    def all_records(self) -> list[JobRecord]:
        return list(self._records.values())
