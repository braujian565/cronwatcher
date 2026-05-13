"""Track and report runtime variance for cron jobs.

Computes how much a job's duration deviates from its historical average,
flagging jobs whose runtimes are unusually long or short.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

from cronwatcher.metrics import JobMetrics, get_all_metrics
from cronwatcher.job_store import JobStore


@dataclass
class VarianceReport:
    job_name: str
    avg_duration: Optional[float]   # seconds
    std_dev: Optional[float]        # seconds
    last_duration: Optional[float]  # seconds
    z_score: Optional[float]        # standard deviations from mean
    flagged: bool = False

    def __str__(self) -> str:
        if self.avg_duration is None:
            return f"{self.job_name}: no runtime history"
        flag = " [FLAGGED]" if self.flagged else ""
        return (
            f"{self.job_name}: last={self.last_duration:.1f}s "
            f"avg={self.avg_duration:.1f}s "
            f"std={self.std_dev:.1f}s "
            f"z={self.z_score:.2f}{flag}"
        )


def _std_dev(durations: List[float], mean: float) -> float:
    """Population standard deviation."""
    if len(durations) < 2:
        return 0.0
    variance = sum((d - mean) ** 2 for d in durations) / len(durations)
    return math.sqrt(variance)


def compute_variance(job_name: str, store: JobStore, threshold_z: float = 2.0) -> VarianceReport:
    """Return a VarianceReport for *job_name* using records in *store*."""
    record = store.get(job_name)
    durations = [
        r["duration"] for r in getattr(record, "history", [])
        if r.get("duration") is not None
    ]

    if not durations:
        return VarianceReport(
            job_name=job_name,
            avg_duration=None,
            std_dev=None,
            last_duration=None,
            z_score=None,
            flagged=False,
        )

    mean = sum(durations) / len(durations)
    std = _std_dev(durations, mean)
    last = durations[-1]
    z = (last - mean) / std if std > 0 else 0.0
    flagged = abs(z) >= threshold_z

    return VarianceReport(
        job_name=job_name,
        avg_duration=round(mean, 3),
        std_dev=round(std, 3),
        last_duration=round(last, 3),
        z_score=round(z, 4),
        flagged=flagged,
    )


def check_all_variances(
    store: JobStore,
    threshold_z: float = 2.0,
) -> List[VarianceReport]:
    """Return variance reports for every job tracked in *store*."""
    job_names = list(store.all_jobs())
    return [compute_variance(name, store, threshold_z) for name in sorted(job_names)]
