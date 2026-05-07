"""Job dependency tracking — skip a job if its declared dependencies failed."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronwatcher.config import JobConfig
from cronwatcher.job_store import JobStore


@dataclass
class DependencyResult:
    job_name: str
    blocked_by: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.blocked_by) == 0

    def __str__(self) -> str:
        if self.ok:
            return f"{self.job_name}: all dependencies satisfied"
        deps = ", ".join(self.blocked_by)
        return f"{self.job_name}: blocked by failed/never-run dependencies: {deps}"


def check_dependencies(
    job: JobConfig,
    store: JobStore,
    all_jobs: Optional[List[JobConfig]] = None,
) -> DependencyResult:
    """Return a DependencyResult indicating whether *job* may run.

    A dependency blocks execution when:
    - it has never been recorded in the store, OR
    - its most recent run was a failure (exit_code != 0).
    """
    depends_on: List[str] = getattr(job, "depends_on", None) or []
    if not depends_on:
        return DependencyResult(job_name=job.name)

    blocked_by: List[str] = []
    for dep_name in depends_on:
        record = store.get(dep_name)
        if record is None:
            blocked_by.append(dep_name)
            continue
        if record.last_exit_code is None or record.last_exit_code != 0:
            blocked_by.append(dep_name)

    return DependencyResult(job_name=job.name, blocked_by=blocked_by)


def filter_runnable_jobs(
    jobs: List[JobConfig],
    store: JobStore,
) -> List[JobConfig]:
    """Return only those jobs whose dependencies are all satisfied."""
    runnable = []
    for job in jobs:
        result = check_dependencies(job, store, all_jobs=jobs)
        if result.ok:
            runnable.append(job)
    return runnable
