"""Core watcher logic: runs jobs, records results, triggers alerts."""

import logging
from typing import Callable, Optional

from cronwatcher.config import AppConfig, JobConfig
from cronwatcher.job_store import JobRecord, JobStore
from cronwatcher.runner import RunResult, run_job

logger = logging.getLogger(__name__)

AlertCallback = Callable[[JobConfig, RunResult, JobRecord], None]


class Watcher:
    """Orchestrates job execution, state tracking, and alert dispatch."""

    def __init__(
        self,
        config: AppConfig,
        store: JobStore,
        alert_callback: Optional[AlertCallback] = None,
    ):
        self.config = config
        self.store = store
        self.alert_callback = alert_callback

    def run_job(self, job: JobConfig) -> RunResult:
        """Execute a single job, update store, and alert if needed."""
        logger.info("Running job '%s': %s", job.name, job.command)
        result = run_job(job)

        if result.success:
            record = self.store.record_success(job.name)
            logger.info(
                "Job '%s' succeeded in %.3fs", job.name, result.duration_seconds
            )
        else:
            record = self.store.record_failure(job.name, result.exit_code)
            logger.warning(
                "Job '%s' failed (exit %d), consecutive failures: %d",
                job.name,
                result.exit_code,
                record.consecutive_failures,
            )
            self._maybe_alert(job, result, record)

        return result

    def run_all(self) -> list[RunResult]:
        """Run all configured jobs sequentially."""
        results = []
        for job in self.config.jobs:
            results.append(self.run_job(job))
        return results

    def _maybe_alert(self, job: JobConfig, result: RunResult, record: JobRecord) -> None:
        threshold = job.alert_after_failures or self.config.alert.default_failure_threshold
        if record.consecutive_failures >= threshold and self.alert_callback:
            logger.debug("Dispatching alert for job '%s'", job.name)
            self.alert_callback(job, result, record)
