"""Watchdog: detects jobs that have been running longer than expected."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from cronwatcher.config import AppConfig, JobConfig
from cronwatcher.runlock import RunLock


@dataclass
class StuckJob:
    job_name: str
    pid: int
    started_at: datetime
    running_seconds: float
    timeout_seconds: Optional[int]

    def __str__(self) -> str:
        mins = self.running_seconds / 60
        limit = (
            f", limit={self.timeout_seconds}s" if self.timeout_seconds is not None else ""
        )
        return (
            f"{self.job_name}: pid={self.pid} running {mins:.1f}m"
            f" ({self.running_seconds:.0f}s{limit})"
        )


def _job_map(app_config: AppConfig) -> dict[str, JobConfig]:
    return {j.name: j for j in app_config.jobs}


def check_stuck_jobs(
    app_config: AppConfig,
    lock: RunLock,
    *,
    default_warn_after: int = 3600,
) -> List[StuckJob]:
    """Return jobs whose lock has been held longer than their timeout (or default)."""
    now = datetime.now(tz=timezone.utc)
    jobs = _job_map(app_config)
    stuck: List[StuckJob] = []

    for entry in lock.all_active():
        job_cfg = jobs.get(entry.job_name)
        timeout = (
            job_cfg.timeout_seconds if job_cfg and job_cfg.timeout_seconds else default_warn_after
        )
        started = entry.acquired_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        elapsed = (now - started).total_seconds()
        if elapsed > timeout:
            stuck.append(
                StuckJob(
                    job_name=entry.job_name,
                    pid=entry.pid,
                    started_at=started,
                    running_seconds=elapsed,
                    timeout_seconds=timeout,
                )
            )

    return stuck
