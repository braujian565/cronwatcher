"""Retry policy evaluation for failed cron jobs."""
from __future__ import annotations

import time
import logging
from dataclasses import dataclass
from typing import Optional

from cronwatcher.config import JobConfig
from cronwatcher.runner import RunResult, run_job

log = logging.getLogger(__name__)


@dataclass
class RetryResult:
    """Outcome after applying the retry policy to a failed job."""
    attempts: int          # total attempts including the first run
    final: RunResult       # result of the last attempt
    gave_up: bool          # True when all retries exhausted without success

    @property
    def succeeded(self) -> bool:
        return self.final.exit_code == 0


def should_retry(job: JobConfig) -> bool:
    """Return True when the job has a retry policy configured."""
    return (job.retry_attempts is not None and job.retry_attempts > 0)


def run_with_retry(
    job: JobConfig,
    first_result: Optional[RunResult] = None,
    *,
    _sleep: callable = time.sleep,
) -> RetryResult:
    """Run *job*, retrying up to ``job.retry_attempts`` times on failure.

    Parameters
    ----------
    job:
        The job configuration.  ``retry_attempts`` and ``retry_delay``
        (seconds, default 0) are read from this object.
    first_result:
        If the caller already has an initial ``RunResult`` it can be passed
        here to avoid a duplicate execution.
    _sleep:
        Injected for testing so tests don't actually sleep.
    """
    max_retries: int = getattr(job, "retry_attempts", 0) or 0
    delay: float = float(getattr(job, "retry_delay", 0) or 0)

    result = first_result if first_result is not None else run_job(job)
    attempts = 1

    while result.exit_code != 0 and attempts <= max_retries:
        log.info(
            "Job '%s' failed (attempt %d/%d), retrying in %.1fs …",
            job.name, attempts, max_retries + 1, delay,
        )
        if delay > 0:
            _sleep(delay)
        result = run_job(job)
        attempts += 1

    gave_up = result.exit_code != 0
    if gave_up:
        log.warning("Job '%s' gave up after %d attempt(s).", job.name, attempts)
    else:
        log.info("Job '%s' succeeded on attempt %d.", job.name, attempts)

    return RetryResult(attempts=attempts, final=result, gave_up=gave_up)
