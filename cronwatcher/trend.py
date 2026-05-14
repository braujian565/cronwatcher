"""Trend analysis: detect whether a job's failure rate is improving or worsening."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from cronwatcher.job_store import JobStore


@dataclass
class TrendReport:
    job_name: str
    window_size: int
    recent_failure_rate: float   # last half of window
    earlier_failure_rate: float  # first half of window
    direction: str               # "improving", "worsening", "stable"
    delta: float                 # recent - earlier (positive = worse)

    def __str__(self) -> str:
        symbol = {"improving": "↓", "worsening": "↑", "stable": "→"}[self.direction]
        return (
            f"{self.job_name}: {self.direction} {symbol}  "
            f"earlier={self.earlier_failure_rate:.0%}  "
            f"recent={self.recent_failure_rate:.0%}  "
            f"(Δ{self.delta:+.0%})"
        )


def _failure_rate(outcomes: List[bool]) -> float:
    """Return fraction of True (failure) values; 0.0 for empty list."""
    if not outcomes:
        return 0.0
    return sum(outcomes) / len(outcomes)


def compute_trend(
    job_name: str,
    store: JobStore,
    window: int = 20,
    stable_threshold: float = 0.05,
) -> Optional[TrendReport]:
    """Analyse the last *window* runs for *job_name*.

    Returns None when there are fewer than 4 runs (not enough data).
    """
    record = store.get(job_name)
    history = record.history if record else []

    if len(history) < 4:
        return None

    recent_runs = history[-window:]
    mid = len(recent_runs) // 2
    earlier_outcomes = [not r.get("success", True) for r in recent_runs[:mid]]
    recent_outcomes = [not r.get("success", True) for r in recent_runs[mid:]]

    earlier_rate = _failure_rate(earlier_outcomes)
    recent_rate = _failure_rate(recent_outcomes)
    delta = recent_rate - earlier_rate

    if abs(delta) <= stable_threshold:
        direction = "stable"
    elif delta > 0:
        direction = "worsening"
    else:
        direction = "improving"

    return TrendReport(
        job_name=job_name,
        window_size=len(recent_runs),
        recent_failure_rate=recent_rate,
        earlier_failure_rate=earlier_rate,
        direction=direction,
        delta=delta,
    )


def check_all_trends(
    store: JobStore,
    job_names: List[str],
    window: int = 20,
    stable_threshold: float = 0.05,
) -> List[TrendReport]:
    """Return TrendReports for every job that has enough history."""
    reports = []
    for name in job_names:
        report = compute_trend(name, store, window=window, stable_threshold=stable_threshold)
        if report is not None:
            reports.append(report)
    return reports
