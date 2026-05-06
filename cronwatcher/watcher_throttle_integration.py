"""Integration helpers: apply throttle logic inside the Watcher alert path.

This module is intentionally thin — it wires Throttler into the existing
Watcher._maybe_alert flow without modifying watcher.py directly.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from cronwatcher.config import AppConfig, JobConfig
from cronwatcher.job_store import JobRecord
from cronwatcher.throttle import Throttler

logger = logging.getLogger(__name__)

_DEFAULT_STATE = Path(".cronwatcher/throttle.json")


def make_throttler(cfg: AppConfig) -> Throttler:
    """Build a Throttler from AppConfig, falling back to sensible defaults."""
    cooldown = getattr(cfg, "alert_cooldown_seconds", 3600)
    state_path = Path(getattr(cfg, "throttle_state_path", str(_DEFAULT_STATE)))
    return Throttler(state_path=state_path, cooldown_seconds=cooldown)


def should_send_alert(
    job: JobConfig,
    record: JobRecord,
    throttler: Throttler,
    min_failures: int = 1,
) -> bool:
    """Return True when an alert should fire for *job* given its *record*.

    Rules:
    - consecutive_failures must reach *min_failures*
    - the alert must not be suppressed by the throttler
    """
    if record.consecutive_failures < min_failures:
        return False
    if throttler.is_suppressed(job.name):
        logger.debug("Alert for '%s' suppressed by throttle.", job.name)
        return False
    return True


def after_alert_sent(job_name: str, throttler: Throttler) -> None:
    """Call this after an alert has been dispatched to record it."""
    throttler.record_alert(job_name)


def after_job_success(job_name: str, throttler: Throttler) -> None:
    """Call this after a successful run to clear the throttle state."""
    throttler.reset(job_name)
