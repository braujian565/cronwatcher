"""Environment variable validation for cron jobs.

Allows jobs to declare required environment variables; reports
missing or empty vars before a job is executed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
import os

from cronwatcher.config import JobConfig


@dataclass
class EnvCheckResult:
    job_name: str
    missing: List[str] = field(default_factory=list)
    empty: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing and not self.empty

    def __str__(self) -> str:
        parts: List[str] = []
        if self.missing:
            parts.append("missing: " + ", ".join(self.missing))
        if self.empty:
            parts.append("empty: " + ", ".join(self.empty))
        if not parts:
            return f"{self.job_name}: env OK"
        return f"{self.job_name}: env problems — " + "; ".join(parts)


def check_env(job: JobConfig) -> EnvCheckResult:
    """Check that all required_env vars are present and non-empty."""
    required: List[str] = getattr(job, "required_env", None) or []
    result = EnvCheckResult(job_name=job.name)
    for var in required:
        value: Optional[str] = os.environ.get(var)
        if value is None:
            result.missing.append(var)
        elif value.strip() == "":
            result.empty.append(var)
    return result


def check_all_envs(jobs: List[JobConfig]) -> List[EnvCheckResult]:
    """Run env checks for every job; return only failing results."""
    return [r for r in (check_env(j) for j in jobs) if not r.ok]
