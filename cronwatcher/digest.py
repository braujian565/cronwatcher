"""Daily/periodic digest report of all monitored cron job statuses."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List

from cronwatcher.config import AppConfig
from cronwatcher.history import build_history, format_history_table
from cronwatcher.job_store import JobStore

logger = logging.getLogger(__name__)


@dataclass
class DigestReport:
    generated_at: datetime
    total_jobs: int
    ok_count: int
    failing_count: int
    never_run_count: int
    table: str

    def summary_line(self) -> str:
        return (
            f"{self.total_jobs} jobs — "
            f"{self.ok_count} OK, "
            f"{self.failing_count} failing, "
            f"{self.never_run_count} never run"
        )


def build_digest(config: AppConfig, store: JobStore) -> DigestReport:
    """Build a digest report from the current job store state."""
    entries = build_history(config, store)
    table = format_history_table(entries)

    ok = sum(1 for e in entries if e.status == "OK")
    failing = sum(1 for e in entries if e.status == "FAILING")
    never = sum(1 for e in entries if e.status == "NEVER RUN")

    return DigestReport(
        generated_at=datetime.utcnow(),
        total_jobs=len(entries),
        ok_count=ok,
        failing_count=failing,
        never_run_count=never,
        table=table,
    )


def send_digest(config: AppConfig, store: JobStore) -> None:
    """Build and dispatch a digest via all configured alert channels."""
    from cronwatcher.notifier import get_channels

    report = build_digest(config, store)
    subject = f"[cronwatcher] Daily digest — {report.summary_line()}"
    body = f"Digest generated at {report.generated_at.strftime('%Y-%m-%d %H:%M')} UTC\n\n{report.table}"

    channels = get_channels()
    for name, handler in channels.items():
        try:
            handler(subject, body, config.alert, record=None)
        except Exception as exc:  # pragma: no cover
            logger.warning("Digest channel %s failed: %s", name, exc)

    logger.info("Digest sent via %d channel(s): %s", len(channels), report.summary_line())
