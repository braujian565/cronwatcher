"""Provides job execution history reporting utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from cronwatcher.job_store import JobRecord, JobStore


@dataclass
class HistoryEntry:
    job_name: str
    last_run: Optional[str]
    last_exit_code: Optional[int]
    consecutive_failures: int
    total_runs: int
    status: str  # "ok", "failing", "never_run"

    def as_row(self) -> List[str]:
        """Return a list of string columns suitable for tabular display."""
        return [
            self.job_name,
            self.last_run or "—",
            str(self.last_exit_code) if self.last_exit_code is not None else "—",
            str(self.consecutive_failures),
            str(self.total_runs),
            self.status,
        ]


HEADER: List[str] = [
    "Job",
    "Last Run",
    "Exit Code",
    "Consec. Failures",
    "Total Runs",
    "Status",
]


def _status(record: JobRecord) -> str:
    if record.total_runs == 0:
        return "never_run"
    if record.consecutive_failures > 0:
        return "failing"
    return "ok"


def build_history(store: JobStore, job_names: Optional[List[str]] = None) -> List[HistoryEntry]:
    """Return HistoryEntry objects for the requested jobs (all if *job_names* is None)."""
    names = job_names if job_names is not None else store.all_job_names()
    entries: List[HistoryEntry] = []
    for name in sorted(names):
        record = store.get(name)
        entries.append(
            HistoryEntry(
                job_name=name,
                last_run=record.last_run,
                last_exit_code=record.last_exit_code,
                consecutive_failures=record.consecutive_failures,
                total_runs=record.total_runs,
                status=_status(record),
            )
        )
    return entries


def format_history_table(entries: List[HistoryEntry]) -> str:
    """Format history entries as a plain-text table."""
    if not entries:
        return "No job history available."

    rows = [HEADER] + [e.as_row() for e in entries]
    col_widths = [max(len(row[i]) for row in rows) for i in range(len(HEADER))]
    sep = "  ".join("-" * w for w in col_widths)
    lines = []
    lines.append("  ".join(h.ljust(col_widths[i]) for i, h in enumerate(HEADER)))
    lines.append(sep)
    for row in rows[1:]:
        lines.append("  ".join(row[i].ljust(col_widths[i]) for i in range(len(HEADER))))
    return "\n".join(lines)
