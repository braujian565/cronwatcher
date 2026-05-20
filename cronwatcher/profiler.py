"""Job execution profiler.

Tracks per-job runtime statistics (min, max, p50, p95) derived from
historical run durations stored in the JobStore.  Results can be used
by the CLI or alerting pipeline to flag jobs whose execution time has
drifted significantly from their baseline.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

from cronwatcher.job_store import JobStore
from cronwatcher.config import AppConfig


@dataclass
class ProfileReport:
    """Runtime profile for a single job."""

    job_name: str
    sample_count: int
    min_seconds: Optional[float]
    max_seconds: Optional[float]
    p50_seconds: Optional[float]  # median
    p95_seconds: Optional[float]
    mean_seconds: Optional[float]

    def __str__(self) -> str:  # pragma: no cover
        if self.sample_count == 0:
            return f"{self.job_name}: no data"
        return (
            f"{self.job_name}: "
            f"n={self.sample_count} "
            f"min={self.min_seconds:.1f}s "
            f"p50={self.p50_seconds:.1f}s "
            f"p95={self.p95_seconds:.1f}s "
            f"max={self.max_seconds:.1f}s"
        )


def _percentile(sorted_values: List[float], pct: float) -> float:
    """Return the *pct*-th percentile (0–100) of a pre-sorted list.

    Uses the nearest-rank method so no interpolation is needed.
    """
    if not sorted_values:
        raise ValueError("Cannot compute percentile of empty list")
    index = math.ceil(pct / 100.0 * len(sorted_values)) - 1
    index = max(0, min(index, len(sorted_values) - 1))
    return sorted_values[index]


def _durations_for_job(store: JobStore, job_name: str) -> List[float]:
    """Return a sorted list of successful run durations (seconds) for *job_name*."""
    record = store.get(job_name)
    if record is None:
        return []

    durations: List[float] = []
    for entry in record.get("history", []):
        # Only include successful runs that recorded a duration.
        if entry.get("exit_code") == 0 and entry.get("duration_seconds") is not None:
            durations.append(float(entry["duration_seconds"]))

    return sorted(durations)


def compute_profile(store: JobStore, job_name: str) -> ProfileReport:
    """Build a :class:`ProfileReport` for *job_name* using data in *store*."""
    durations = _durations_for_job(store, job_name)
    n = len(durations)

    if n == 0:
        return ProfileReport(
            job_name=job_name,
            sample_count=0,
            min_seconds=None,
            max_seconds=None,
            p50_seconds=None,
            p95_seconds=None,
            mean_seconds=None,
        )

    return ProfileReport(
        job_name=job_name,
        sample_count=n,
        min_seconds=durations[0],
        max_seconds=durations[-1],
        p50_seconds=_percentile(durations, 50),
        p95_seconds=_percentile(durations, 95),
        mean_seconds=sum(durations) / n,
    )


def compute_all_profiles(
    app_config: AppConfig, store: JobStore
) -> List[ProfileReport]:
    """Return a :class:`ProfileReport` for every job defined in *app_config*."""
    return [
        compute_profile(store, job.name)
        for job in app_config.jobs
    ]


def format_profile_table(reports: List[ProfileReport]) -> str:
    """Render *reports* as a plain-text table suitable for terminal output."""
    if not reports:
        return "No profile data available."

    header = f"{'JOB':<30} {'N':>5} {'MIN':>8} {'P50':>8} {'P95':>8} {'MAX':>8}"
    separator = "-" * len(header)
    rows = [header, separator]

    for r in reports:
        if r.sample_count == 0:
            rows.append(f"{r.job_name:<30} {'0':>5} {'n/a':>8} {'n/a':>8} {'n/a':>8} {'n/a':>8}")
        else:
            rows.append(
                f"{r.job_name:<30} "
                f"{r.sample_count:>5} "
                f"{r.min_seconds:>7.1f}s "
                f"{r.p50_seconds:>7.1f}s "
                f"{r.p95_seconds:>7.1f}s "
                f"{r.max_seconds:>7.1f}s"
            )

    return "\n".join(rows)
