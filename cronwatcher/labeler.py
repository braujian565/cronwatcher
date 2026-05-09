"""Assign and query human-readable labels (aliases) for cron jobs.

Labels are stored in a JSON file alongside the job store so they survive
restarts.  A label is just a short string that operators can set via the
CLI to make dashboards and digest reports more readable.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from cronwatcher.config import JobConfig

_DEFAULT_PATH = Path("cronwatcher_labels.json")


@dataclass
class Labeler:
    """Persist and query job labels."""

    path: Path = field(default_factory=lambda: _DEFAULT_PATH)
    _data: Dict[str, str] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text())
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_label(self, job_name: str, label: str) -> None:
        """Assign *label* to *job_name* and persist."""
        self._data[job_name] = label
        self._save()

    def remove_label(self, job_name: str) -> bool:
        """Remove the label for *job_name*.  Returns True if it existed."""
        existed = job_name in self._data
        self._data.pop(job_name, None)
        if existed:
            self._save()
        return existed

    def get_label(self, job_name: str) -> Optional[str]:
        """Return the label for *job_name*, or None if not set."""
        return self._data.get(job_name)

    def display_name(self, job_name: str) -> str:
        """Return label if set, otherwise the raw job name."""
        return self._data.get(job_name, job_name)

    def all_labels(self) -> Dict[str, str]:
        """Return a copy of the full label mapping."""
        return dict(self._data)

    def filter_by_label(self, jobs: List[JobConfig], label: str) -> List[JobConfig]:
        """Return jobs whose label (or name) matches *label* (case-insensitive)."""
        label_lower = label.lower()
        return [
            j for j in jobs
            if self.display_name(j.name).lower() == label_lower
        ]
