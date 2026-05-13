"""Per-job timeout policy with fallback to global default."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from cronwatcher.config import AppConfig, JobConfig


@dataclass
class TimeoutPolicy:
    """Resolved timeout settings for a single job."""

    job_name: str
    timeout_seconds: int
    source: str  # 'job' | 'global' | 'default'

    def __str__(self) -> str:
        return (
            f"{self.job_name}: {self.timeout_seconds}s (from {self.source})"
        )


_HARD_DEFAULT_SECONDS = 60


def resolve_timeout(job: JobConfig, app_config: AppConfig) -> TimeoutPolicy:
    """Return the effective timeout for *job*.

    Resolution order:
      1. ``job.timeout`` (if set and > 0)
      2. ``app_config.default_timeout`` (if set and > 0)
      3. Module-level hard default (60 s)
    """
    if job.timeout and job.timeout > 0:
        return TimeoutPolicy(
            job_name=job.name,
            timeout_seconds=job.timeout,
            source="job",
        )

    global_timeout: Optional[int] = getattr(app_config, "default_timeout", None)
    if global_timeout and global_timeout > 0:
        return TimeoutPolicy(
            job_name=job.name,
            timeout_seconds=global_timeout,
            source="global",
        )

    return TimeoutPolicy(
        job_name=job.name,
        timeout_seconds=_HARD_DEFAULT_SECONDS,
        source="default",
    )


def resolve_all_timeouts(
    app_config: AppConfig,
) -> list[TimeoutPolicy]:
    """Return resolved :class:`TimeoutPolicy` for every job in *app_config*."""
    return [resolve_timeout(job, app_config) for job in app_config.jobs]
