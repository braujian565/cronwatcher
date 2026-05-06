"""Heartbeat tracker: detects jobs that were expected to run but never did."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

from cronwatcher.config import AppConfig, JobConfig
from cronwatcher.job_store import JobRecord, JobStore
from cronwatcher.scheduler import is_job_due


@dataclass
class MissedJob:
    """Represents a job that was expected to run but has no recent record."""

    job: JobConfig
    last_run: datetime | None
    expected_by: datetime

    def __str__(self) -> str:
        last = self.last_run.isoformat() if self.last_run else "never"
        return (
            f"Job '{self.job.name}' missed heartbeat — "
            f"expected by {self.expected_by.isoformat()}, last run: {last}"
        )


def _last_run_dt(record: JobRecord | None) -> datetime | None:
    """Return the last_run datetime from a record, or None."""
    if record is None or record.last_run is None:
        return None
    if isinstance(record.last_run, datetime):
        return record.last_run
    return datetime.fromisoformat(record.last_run)


def check_missed_jobs(
    config: AppConfig,
    store: JobStore,
    now: datetime | None = None,
    grace_minutes: int = 5,
) -> List[MissedJob]:
    """Return jobs that were due but have not run within the grace window.

    A job is considered missed when:
    - It was due at or before ``now``.
    - Its last recorded run is older than ``now - grace_minutes``.
    """
    if now is None:
        now = datetime.now()

    missed: List[MissedJob] = []
    cutoff = now - timedelta(minutes=grace_minutes)

    for job in config.jobs:
        if not is_job_due(job, config, now):
            continue

        record = store.get(job.name)
        last_run = _last_run_dt(record)

        if last_run is None or last_run < cutoff:
            missed.append(
                MissedJob(
                    job=job,
                    last_run=last_run,
                    expected_by=now,
                )
            )

    return missed
