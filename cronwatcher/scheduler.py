"""Scheduler: determines which jobs are due to run based on cron expressions."""

from __future__ import annotations

from datetime import datetime
from typing import List

from croniter import croniter

from cronwatcher.config import AppConfig, JobConfig


def is_job_due(job: JobConfig, now: datetime | None = None) -> bool:
    """Return True if the job's cron schedule is due at *now* (or current UTC time).

    A job is considered due when the most recent scheduled tick is within the
    last 60 seconds relative to *now*.  This gives a one-minute window that
    matches the minimum cron resolution.
    """
    if now is None:
        now = datetime.utcnow()

    try:
        cron = croniter(job.schedule, now)
    except (ValueError, KeyError) as exc:
        raise ValueError(f"Invalid cron expression '{job.schedule}' for job '{job.name}': {exc}") from exc

    prev_tick: datetime = cron.get_prev(datetime)  # type: ignore[assignment]
    delta_seconds = (now - prev_tick).total_seconds()
    return 0 <= delta_seconds < 60


def get_due_jobs(config: AppConfig, now: datetime | None = None) -> List[JobConfig]:
    """Return all jobs from *config* whose schedule is due at *now*."""
    if now is None:
        now = datetime.utcnow()
    return [job for job in config.jobs if is_job_due(job, now)]
