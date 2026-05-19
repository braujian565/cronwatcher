"""Exponential back-off policy for alert / retry delays."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BackoffPolicy:
    """Configurable exponential back-off with optional jitter and cap."""

    base_seconds: float = 60.0
    multiplier: float = 2.0
    max_seconds: float = 3600.0
    jitter: bool = False

    def __str__(self) -> str:
        return (
            f"BackoffPolicy(base={self.base_seconds}s, "
            f"multiplier={self.multiplier}, max={self.max_seconds}s, "
            f"jitter={self.jitter})"
        )

    def delay(self, attempt: int) -> float:
        """Return the back-off delay (seconds) for *attempt* (0-based).

        attempt=0 → base_seconds
        attempt=1 → base * multiplier
        …capped at max_seconds.
        """
        if attempt < 0:
            attempt = 0
        raw = self.base_seconds * (self.multiplier ** attempt)
        capped = min(raw, self.max_seconds)
        if self.jitter:
            import random
            capped = random.uniform(0, capped)
        return capped


def parse_backoff(raw: Optional[dict]) -> BackoffPolicy:
    """Build a BackoffPolicy from a raw config dict (or None → defaults)."""
    if not raw:
        return BackoffPolicy()
    return BackoffPolicy(
        base_seconds=float(raw.get("base_seconds", 60.0)),
        multiplier=float(raw.get("multiplier", 2.0)),
        max_seconds=float(raw.get("max_seconds", 3600.0)),
        jitter=bool(raw.get("jitter", False)),
    )


def resolve_backoff(app_config, job) -> BackoffPolicy:  # type: ignore[type-arg]
    """Return the effective BackoffPolicy for *job*, falling back to global."""
    raw_job = getattr(job, "backoff", None)
    if raw_job is not None:
        return parse_backoff(raw_job if isinstance(raw_job, dict) else None)
    raw_global = getattr(getattr(app_config, "defaults", None), "backoff", None)
    return parse_backoff(raw_global if isinstance(raw_global, dict) else None)
