"""Tests for cronwatcher.watchdog and cronwatcher.cli_watchdog."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.watchdog import StuckJob, check_stuck_jobs
from cronwatcher.runlock import LockEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app_config(jobs=None):
    cfg = MagicMock()
    cfg.jobs = jobs or []
    return cfg


def _make_job(name: str, timeout: int | None = None):
    j = MagicMock()
    j.name = name
    j.timeout_seconds = timeout
    return j


def _make_lock(entries):
    lock = MagicMock()
    lock.all_active.return_value = entries
    return lock


def _entry(name: str, pid: int, seconds_ago: float) -> LockEntry:
    acquired = datetime.now(tz=timezone.utc) - timedelta(seconds=seconds_ago)
    e = MagicMock(spec=LockEntry)
    e.job_name = name
    e.pid = pid
    e.acquired_at = acquired
    return e


# ---------------------------------------------------------------------------
# check_stuck_jobs
# ---------------------------------------------------------------------------

def test_no_stuck_when_lock_empty():
    cfg = _make_app_config()
    lock = _make_lock([])
    assert check_stuck_jobs(cfg, lock) == []


def test_not_stuck_when_within_timeout():
    job = _make_job("backup", timeout=600)
    cfg = _make_app_config([job])
    lock = _make_lock([_entry("backup", 1234, seconds_ago=300)])
    assert check_stuck_jobs(cfg, lock) == []


def test_stuck_when_exceeds_job_timeout():
    job = _make_job("backup", timeout=600)
    cfg = _make_app_config([job])
    lock = _make_lock([_entry("backup", 1234, seconds_ago=700)])
    result = check_stuck_jobs(cfg, lock)
    assert len(result) == 1
    assert result[0].job_name == "backup"
    assert result[0].pid == 1234
    assert result[0].running_seconds >= 700


def test_stuck_uses_default_warn_after_when_no_timeout():
    job = _make_job("cleanup", timeout=None)
    cfg = _make_app_config([job])
    lock = _make_lock([_entry("cleanup", 9999, seconds_ago=200)])
    # default is 3600 — 200s should NOT be stuck
    assert check_stuck_jobs(cfg, lock, default_warn_after=3600) == []


def test_stuck_uses_default_warn_after_exceeded():
    job = _make_job("cleanup", timeout=None)
    cfg = _make_app_config([job])
    lock = _make_lock([_entry("cleanup", 9999, seconds_ago=4000)])
    result = check_stuck_jobs(cfg, lock, default_warn_after=3600)
    assert len(result) == 1


def test_unknown_job_in_lock_uses_default():
    cfg = _make_app_config(jobs=[])  # no matching job config
    lock = _make_lock([_entry("orphan", 42, seconds_ago=5000)])
    result = check_stuck_jobs(cfg, lock, default_warn_after=3600)
    assert len(result) == 1
    assert result[0].job_name == "orphan"


def test_str_representation():
    s = StuckJob(
        job_name="myjob",
        pid=123,
        started_at=datetime.now(tz=timezone.utc),
        running_seconds=7200,
        timeout_seconds=3600,
    )
    text = str(s)
    assert "myjob" in text
    assert "123" in text
    assert "3600s" in text


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_cmd_watchdog_no_stuck(tmp_path, capsys):
    from cronwatcher.cli_watchdog import cmd_watchdog

    args = argparse.Namespace(
        config=str(tmp_path / "nonexistent.yaml"),
        lock_dir=str(tmp_path / "locks"),
        warn_after=3600,
    )
    with pytest.raises(SystemExit):
        cmd_watchdog(args)


def test_cmd_watchdog_prints_stuck(tmp_path, capsys):
    from cronwatcher.cli_watchdog import cmd_watchdog

    job = _make_job("slow_job", timeout=60)
    app_cfg = _make_app_config([job])
    lock = _make_lock([_entry("slow_job", 555, seconds_ago=120)])

    args = argparse.Namespace(
        config="fake.yaml",
        lock_dir=str(tmp_path / "locks"),
        warn_after=3600,
    )

    with patch("cronwatcher.cli_watchdog.load_config", return_value=app_cfg), \
         patch("cronwatcher.cli_watchdog.RunLock", return_value=lock):
        cmd_watchdog(args)

    out = capsys.readouterr().out
    assert "slow_job" in out
    assert "555" in out


def test_register_watchdog_subcommand():
    from cronwatcher.cli_watchdog import register_watchdog_subcommand

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_watchdog_subcommand(sub)
    args = parser.parse_args(["watchdog"])
    assert hasattr(args, "func")
