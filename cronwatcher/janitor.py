"""Janitor: prune stale records and old history entries from the job store."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List

from cronwatcher.job_store import JobStore

log = logging.getLogger(__name__)


@dataclass
class JanitorResult:
    jobs_pruned: List[str]
    records_cleared: int

    def __str__(self) -> str:
        if not self.jobs_pruned and self.records_cleared == 0:
            return "Janitor: nothing to prune."
        parts = []
        if self.jobs_pruned:
            parts.append(f"removed records for {len(self.jobs_pruned)} unknown job(s): {', '.join(self.jobs_pruned)}")
        if self.records_cleared:
            parts.append(f"cleared last_run for {self.records_cleared} stale job(s)")
        return "Janitor: " + "; ".join(parts) + "."


def prune_unknown_jobs(store: JobStore, known_job_names: List[str]) -> List[str]:
    """Delete store records for jobs no longer present in the config."""
    known = set(known_job_names)
    removed: List[str] = []
    for name in list(store._data.keys()):
        if name not in known:
            del store._data[name]
            removed.append(name)
            log.info("Janitor: pruned unknown job %r from store.", name)
    if removed:
        store._save()
    return removed


def clear_stale_last_run(
    store: JobStore,
    known_job_names: List[str],
    max_age_days: int = 90,
) -> int:
    """Zero out last_run timestamps older than *max_age_days* for known jobs."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=max_age_days)
    cleared = 0
    for name in known_job_names:
        record = store._data.get(name)
        if record is None:
            continue
        last = record.get("last_run")
        if last and datetime.fromisoformat(last) < cutoff:
            record["last_run"] = None
            cleared += 1
            log.info("Janitor: cleared stale last_run for job %r (was %s).", name, last)
    if cleared:
        store._save()
    return cleared


def run_janitor(
    store: JobStore,
    known_job_names: List[str],
    max_age_days: int = 90,
) -> JanitorResult:
    """Run all janitor tasks and return a summary result."""
    pruned = prune_unknown_jobs(store, known_job_names)
    cleared = clear_stale_last_run(store, known_job_names, max_age_days=max_age_days)
    result = JanitorResult(jobs_pruned=pruned, records_cleared=cleared)
    log.info(str(result))
    return result
