"""Execution window enforcement — restrict jobs to allowed time ranges."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import List, Optional


@dataclass
class TimeWindow:
    """A single allowed execution window (start inclusive, end exclusive)."""
    start: time  # e.g. time(8, 0)
    end: time    # e.g. time(18, 0)

    def contains(self, dt: datetime) -> bool:
        """Return True if *dt* falls within [start, end)."""
        t = dt.time().replace(second=0, microsecond=0)
        if self.start <= self.end:
            return self.start <= t < self.end
        # Overnight window, e.g. 22:00 – 06:00
        return t >= self.start or t < self.end

    def __str__(self) -> str:
        return f"{self.start.strftime('%H:%M')}-{self.end.strftime('%H:%M')}"


@dataclass
class WindowPolicy:
    """Collection of windows for a single job."""
    job_name: str
    windows: List[TimeWindow] = field(default_factory=list)

    def is_allowed(self, dt: Optional[datetime] = None) -> bool:
        """Return True when *dt* (default: now) falls inside any window."""
        if not self.windows:
            return True  # no restriction
        dt = dt or datetime.now()
        return any(w.contains(dt) for w in self.windows)


def parse_windows(raw: List[str]) -> List[TimeWindow]:
    """Parse a list of 'HH:MM-HH:MM' strings into TimeWindow objects."""
    windows: List[TimeWindow] = []
    for entry in raw:
        parts = entry.strip().split("-")
        if len(parts) != 2:
            raise ValueError(f"Invalid window format '{entry}', expected HH:MM-HH:MM")
        start = time.fromisoformat(parts[0].strip())
        end = time.fromisoformat(parts[1].strip())
        windows.append(TimeWindow(start=start, end=end))
    return windows


def build_window_policy(job_name: str, raw_windows: List[str]) -> WindowPolicy:
    """Convenience factory used by watcher / CLI."""
    return WindowPolicy(job_name=job_name, windows=parse_windows(raw_windows))
