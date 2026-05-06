"""Simple in-memory and file-backed metrics collection for cron job runs."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class JobMetrics:
    job_name: str
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    total_duration_seconds: float = 0.0
    last_duration_seconds: Optional[float] = None
    last_run_at: Optional[str] = None

    @property
    def failure_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return self.failed_runs / self.total_runs

    @property
    def avg_duration_seconds(self) -> Optional[float]:
        if self.total_runs == 0:
            return None
        return self.total_duration_seconds / self.total_runs

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "total_duration_seconds": self.total_duration_seconds,
            "last_duration_seconds": self.last_duration_seconds,
            "last_run_at": self.last_run_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobMetrics":
        return cls(**data)


class MetricsStore:
    def __init__(self, path: str = "/var/lib/cronwatcher/metrics.json") -> None:
        self._path = Path(path)
        self._data: Dict[str, JobMetrics] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text())
                self._data = {k: JobMetrics.from_dict(v) for k, v in raw.items()}
            except (json.JSONDecodeError, TypeError, KeyError):
                self._data = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({k: v.to_dict() for k, v in self._data.items()}, indent=2))

    def get(self, job_name: str) -> JobMetrics:
        if job_name not in self._data:
            self._data[job_name] = JobMetrics(job_name=job_name)
        return self._data[job_name]

    def record(self, job_name: str, success: bool, duration_seconds: float) -> JobMetrics:
        m = self.get(job_name)
        m.total_runs += 1
        m.total_duration_seconds += duration_seconds
        m.last_duration_seconds = duration_seconds
        m.last_run_at = datetime.now(timezone.utc).isoformat()
        if success:
            m.successful_runs += 1
        else:
            m.failed_runs += 1
        self._save()
        return m

    def all_metrics(self) -> List[JobMetrics]:
        return list(self._data.values())
