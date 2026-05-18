"""Integration helpers: apply execution-window enforcement inside Watcher.

Usage (inside Watcher.run_job or run_all)::

    from cronwatcher.watcher_window_integration import job_in_window

    if not job_in_window(job, now=datetime.now()):
        logger.info("Skipping %s — outside execution window", job.name)
        return
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from cronwatcher.config import JobConfig
from cronwatcher.window import WindowPolicy, build_window_policy

logger = logging.getLogger(__name__)


def _policy_for_job(job: JobConfig) -> WindowPolicy:
    raw: List[str] = getattr(job, "windows", None) or []
    return build_window_policy(job.name, raw)


def job_in_window(job: JobConfig, now: Optional[datetime] = None) -> bool:
    """Return True when *job* is allowed to run at *now* (default: current time)."""
    policy = _policy_for_job(job)
    now = now or datetime.now()
    allowed = policy.is_allowed(now)
    if not allowed:
        windows_str = ", ".join(str(w) for w in policy.windows)
        logger.info(
            "Job '%s' skipped: current time %s is outside window(s) [%s]",
            job.name,
            now.strftime("%H:%M"),
            windows_str,
        )
    return allowed


def filter_jobs_in_window(
    jobs: List[JobConfig],
    now: Optional[datetime] = None,
) -> List[JobConfig]:
    """Return only the jobs whose execution window includes *now*."""
    now = now or datetime.now()
    return [j for j in jobs if job_in_window(j, now=now)]
