"""Tag-based filtering for cron jobs.

Allows jobs to be grouped and filtered by arbitrary string tags,
enabling selective execution, alerting, or digest scoping.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from cronwatcher.config import AppConfig, JobConfig


@dataclass
class TagIndex:
    """Inverted index mapping tag -> list of job names."""

    _index: dict[str, list[str]] = field(default_factory=dict)

    def build(self, jobs: Iterable[JobConfig]) -> None:
        """Populate the index from an iterable of JobConfig objects."""
        self._index.clear()
        for job in jobs:
            for tag in job.tags:
                self._index.setdefault(tag, []).append(job.name)

    def jobs_for_tag(self, tag: str) -> List[str]:
        """Return job names associated with *tag* (empty list if unknown)."""
        return list(self._index.get(tag, []))

    def all_tags(self) -> List[str]:
        """Return a sorted list of all known tags."""
        return sorted(self._index.keys())


def filter_jobs_by_tags(
    jobs: Iterable[JobConfig],
    tags: Optional[List[str]],
) -> List[JobConfig]:
    """Return jobs whose tag set intersects *tags*.

    If *tags* is None or empty every job is returned unchanged.
    """
    if not tags:
        return list(jobs)
    tag_set = set(tags)
    return [j for j in jobs if tag_set.intersection(j.tags)]


def jobs_from_app_config(
    app_config: AppConfig,
    tags: Optional[List[str]] = None,
) -> List[JobConfig]:
    """Convenience wrapper: extract and optionally filter jobs from AppConfig."""
    return filter_jobs_by_tags(app_config.jobs, tags)
