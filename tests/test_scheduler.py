"""Tests for cronwatcher.scheduler."""

from datetime import datetime

import pytest

from cronwatcher.config import AlertConfig, AppConfig, JobConfig
from cronwatcher.scheduler import get_due_jobs, is_job_due


def make_job(schedule: str, name: str = "test-job") -> JobConfig:
    return JobConfig(name=name, schedule=schedule, command="echo hi")


def make_app_config(*jobs: JobConfig) -> AppConfig:
    alert = AlertConfig()
    return AppConfig(jobs=list(jobs), alert=alert)


# ---------------------------------------------------------------------------
# is_job_due
# ---------------------------------------------------------------------------

def test_due_at_exact_minute():
    """A job scheduled every minute is always due."""
    job = make_job("* * * * *")
    now = datetime(2024, 1, 15, 12, 0, 0)
    assert is_job_due(job, now) is True


def test_due_within_window():
    """Job is due when we're 30 s after the scheduled tick."""
    job = make_job("0 * * * *")  # top of every hour
    now = datetime(2024, 1, 15, 12, 0, 30)  # 30 s past the hour
    assert is_job_due(job, now) is True


def test_not_due_outside_window():
    """Job is NOT due when we're 90 s after the scheduled tick."""
    job = make_job("0 * * * *")
    now = datetime(2024, 1, 15, 12, 1, 30)  # 90 s past the hour
    assert is_job_due(job, now) is False


def test_invalid_schedule_raises():
    job = make_job("not-a-cron")
    with pytest.raises(ValueError, match="Invalid cron expression"):
        is_job_due(job, datetime(2024, 1, 15, 12, 0, 0))


# ---------------------------------------------------------------------------
# get_due_jobs
# ---------------------------------------------------------------------------

def test_get_due_jobs_returns_due_only():
    hourly = make_job("0 * * * *", name="hourly")
    every_minute = make_job("* * * * *", name="every-minute")
    cfg = make_app_config(hourly, every_minute)

    # 30 s past the hour — both should fire
    now = datetime(2024, 1, 15, 12, 0, 30)
    due = get_due_jobs(cfg, now)
    assert {j.name for j in due} == {"hourly", "every-minute"}


def test_get_due_jobs_none_due():
    hourly = make_job("0 * * * *", name="hourly")
    cfg = make_app_config(hourly)

    # 90 s past the hour — nothing due
    now = datetime(2024, 1, 15, 12, 1, 30)
    assert get_due_jobs(cfg, now) == []


def test_get_due_jobs_empty_config():
    cfg = make_app_config()
    now = datetime(2024, 1, 15, 12, 0, 0)
    assert get_due_jobs(cfg, now) == []
