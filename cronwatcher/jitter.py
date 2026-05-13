"""Jitter support: add randomised delay before running a job to spread load."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Optional

from cronwatcher.config import JobConfig


@dataclass
class JitterPolicy:
    """Resolved jitter settings for a single job."""

    max_seconds: int  # upper bound of the random window (0 means disabled)
    seed: Optional[int] = field(default=None)  # optional fixed seed for tests

    def __str__(self) -> str:
        if self.max_seconds <= 0:
            return "jitter=disabled"
        return f"jitter=0-{self.max_seconds}s"

    @property
    def enabled(self) -> bool:
        return self.max_seconds > 0

    def sample(self) -> int:
        """Return a random delay in seconds within [0, max_seconds]."""
        if not self.enabled:
            return 0
        rng = random.Random(self.seed)
        return rng.randint(0, self.max_seconds)


def resolve_jitter(job: JobConfig, global_max: Optional[int] = None) -> JitterPolicy:
    """Determine the effective jitter policy for *job*.

    Priority: job-level ``jitter_seconds`` > *global_max* > 0 (disabled).
    """
    raw = getattr(job, "jitter_seconds", None)
    if raw is not None:
        return JitterPolicy(max_seconds=int(raw))
    if global_max is not None:
        return JitterPolicy(max_seconds=int(global_max))
    return JitterPolicy(max_seconds=0)


def apply_jitter(policy: JitterPolicy, *, sleep_fn=time.sleep) -> int:
    """Sleep for the sampled delay and return the number of seconds slept."""
    delay = policy.sample()
    if delay > 0:
        sleep_fn(delay)
    return delay
