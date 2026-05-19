"""Forecast next scheduled run times for cron jobs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from cronwatcher.config import AppConfig, JobConfig
from cronwatcher.scheduler import is_job_due


@dataclass
class ForecastEntry:
    job_name: str
    next_run: datetime
    minutes_away: int

    def __str__(self) -> str:
        return (
            f"{self.job_name}: next run at {self.next_run.strftime('%Y-%m-%d %H:%M')} "
            f"(in {self.minutes_away} min)"
        )


def _next_run(job: JobConfig, after: datetime, horizon_minutes: int) -> Optional[datetime]:
    """Scan minute-by-minute up to horizon_minutes to find the next due time."""
    candidate = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(horizon_minutes):
        if is_job_due(job, candidate):
            return candidate
        candidate += timedelta(minutes=1)
    return None


def compute_forecast(
    app_config: AppConfig,
    *,
    after: Optional[datetime] = None,
    horizon_minutes: int = 1440,
) -> List[ForecastEntry]:
    """Return a ForecastEntry for every job whose next run falls within the horizon."""
    now = after or datetime.now()
    entries: List[ForecastEntry] = []
    for job in app_config.jobs:
        nxt = _next_run(job, now, horizon_minutes)
        if nxt is None:
            continue
        delta = int((nxt - now).total_seconds() // 60)
        entries.append(ForecastEntry(job_name=job.name, next_run=nxt, minutes_away=delta))
    entries.sort(key=lambda e: e.next_run)
    return entries


def format_forecast_table(entries: List[ForecastEntry]) -> str:
    """Render forecast entries as a plain-text table."""
    if not entries:
        return "No scheduled jobs found within the forecast horizon."
    header = f"{'JOB':<30} {'NEXT RUN':<20} {'IN (min)':>8}"
    sep = "-" * len(header)
    rows = [
        f"{e.job_name:<30} {e.next_run.strftime('%Y-%m-%d %H:%M'):<20} {e.minutes_away:>8}"
        for e in entries
    ]
    return "\n".join([header, sep] + rows)
