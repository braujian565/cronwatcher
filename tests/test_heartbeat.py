"""Tests for cronwatcher.heartbeat."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from cronwatcher.config import AlertConfig, AppConfig, JobConfig
from cronwatcher.heartbeat import MissedJob, check_missed_jobs
from cronwatcher.job_store import JobStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def store(tmp_path):
    return JobStore(str(tmp_path / "jobs.json"))


def _app_config(*jobs: JobConfig) -> AppConfig:
    alert = AlertConfig(email=None, smtp_host=None, smtp_port=587, from_addr=None)
    return AppConfig(jobs=list(jobs), alert=alert, check_interval=60)


def _job(name: str, schedule: str = "* * * * *") -> JobConfig:
    return JobConfig(name=name, command=f"echo {name}", schedule=schedule)


# A fixed "now" aligned to minute boundary so is_job_due returns True.
NOW = datetime(2024, 6, 1, 12, 0, 0)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_no_missed_when_store_empty_but_job_not_due(store):
    """Jobs with a non-matching schedule should not appear as missed."""
    # Schedule that never matches 12:00 on a Saturday (weekday=5)
    job = _job("weekly", schedule="0 9 * * 1")  # Monday 09:00
    cfg = _app_config(job)
    missed = check_missed_jobs(cfg, store, now=NOW)
    assert missed == []


def test_missed_when_never_run(store):
    """A due job with no record should be reported as missed."""
    job = _job("heartbeat-job")
    cfg = _app_config(job)
    missed = check_missed_jobs(cfg, store, now=NOW, grace_minutes=5)
    assert len(missed) == 1
    assert missed[0].job.name == "heartbeat-job"
    assert missed[0].last_run is None


def test_not_missed_when_run_within_grace(store):
    """A job that ran inside the grace window must not be flagged."""
    job = _job("fresh-job")
    cfg = _app_config(job)
    record = store.get(job.name)
    record.last_run = NOW - timedelta(minutes=2)
    record.last_exit_code = 0
    store.save(record)

    missed = check_missed_jobs(cfg, store, now=NOW, grace_minutes=5)
    assert missed == []


def test_missed_when_run_outside_grace(store):
    """A job whose last run is older than the grace period must be flagged."""
    job = _job("stale-job")
    cfg = _app_config(job)
    record = store.get(job.name)
    record.last_run = NOW - timedelta(minutes=10)
    record.last_exit_code = 0
    store.save(record)

    missed = check_missed_jobs(cfg, store, now=NOW, grace_minutes=5)
    assert len(missed) == 1
    assert missed[0].job.name == "stale-job"


def test_missed_job_str_contains_name(store):
    """MissedJob.__str__ should mention the job name."""
    job = _job("verbose-job")
    cfg = _app_config(job)
    missed = check_missed_jobs(cfg, store, now=NOW, grace_minutes=5)
    assert len(missed) == 1
    assert "verbose-job" in str(missed[0])
    assert "never" in str(missed[0])


def test_multiple_jobs_partial_miss(store):
    """Only the stale job among several should be flagged."""
    job_ok = _job("ok-job")
    job_miss = _job("miss-job")
    cfg = _app_config(job_ok, job_miss)

    rec_ok = store.get(job_ok.name)
    rec_ok.last_run = NOW - timedelta(minutes=1)
    rec_ok.last_exit_code = 0
    store.save(rec_ok)

    missed = check_missed_jobs(cfg, store, now=NOW, grace_minutes=5)
    names = [m.job.name for m in missed]
    assert "miss-job" in names
    assert "ok-job" not in names
