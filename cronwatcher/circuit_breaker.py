"""Circuit breaker: temporarily disable jobs that fail too frequently."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class CircuitState:
    job_name: str
    failure_count: int = 0
    opened_at: Optional[float] = None  # epoch seconds when circuit opened
    reset_after: int = 300  # seconds before auto-reset attempt

    @property
    def is_open(self) -> bool:
        """Circuit is open (job disabled) when failure threshold was hit."""
        return self.opened_at is not None

    @property
    def is_half_open(self) -> bool:
        """Circuit allows one probe run after reset_after seconds."""
        if self.opened_at is None:
            return False
        return (time.time() - self.opened_at) >= self.reset_after

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "failure_count": self.failure_count,
            "opened_at": self.opened_at,
            "reset_after": self.reset_after,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CircuitState":
        return cls(
            job_name=data["job_name"],
            failure_count=data.get("failure_count", 0),
            opened_at=data.get("opened_at"),
            reset_after=data.get("reset_after", 300),
        )


class CircuitBreaker:
    def __init__(self, store_path: Path, threshold: int = 3, reset_after: int = 300):
        self.store_path = store_path
        self.threshold = threshold
        self.reset_after = reset_after
        self._states: Dict[str, CircuitState] = {}
        self._load()

    def _load(self) -> None:
        if self.store_path.exists():
            raw = json.loads(self.store_path.read_text())
            self._states = {k: CircuitState.from_dict(v) for k, v in raw.items()}

    def _save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(json.dumps({k: v.to_dict() for k, v in self._states.items()}, indent=2))

    def get_state(self, job_name: str) -> CircuitState:
        if job_name not in self._states:
            self._states[job_name] = CircuitState(job_name=job_name, reset_after=self.reset_after)
        return self._states[job_name]

    def record_failure(self, job_name: str) -> CircuitState:
        state = self.get_state(job_name)
        state.failure_count += 1
        if state.failure_count >= self.threshold and not state.is_open:
            state.opened_at = time.time()
        self._save()
        return state

    def record_success(self, job_name: str) -> CircuitState:
        state = self.get_state(job_name)
        state.failure_count = 0
        state.opened_at = None
        self._save()
        return state

    def is_allowed(self, job_name: str) -> bool:
        """Return True if the job should be allowed to run."""
        state = self.get_state(job_name)
        if not state.is_open:
            return True
        return state.is_half_open

    def reset(self, job_name: str) -> None:
        if job_name in self._states:
            del self._states[job_name]
            self._save()
