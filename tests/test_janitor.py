"""Tests for cronwatcher.janitor."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.janitor import (
    JanitorResult,
    clear_stale_last_run,
    prune_unknown_jobs,
    run_janitor,
)
from cronwatcher.job_store import JobStore


@pytest.fixture()
def store(tmp_path: Path) -> JobStore:
    s = JobStore(str(tmp_path / "store.json"))
    # Seed two jobs
    s._data = {
        "job_a": {"last_run": None, "last_exit_code": 0, "consecutive_failures": 0},
        "job_b": {"last_run": None, "last_exit_code": 0, "consecutive_failures": 0},
        "job_ghost": {"last_run": None, "last_exit_code": 1, "consecutive_failures": 3},
    }
    s._save()
    return s


def test_prune_unknown_jobs_removes_ghost(store: JobStore) -> None:
    removed = prune_unknown_jobs(store, known_job_names=["job_a", "job_b"])
    assert removed == ["job_ghost"]
    assert "job_ghost" not in store._data


def test_prune_unknown_jobs_keeps_known(store: JobStore) -> None:
    prune_unknown_jobs(store, known_job_names=["job_a", "job_b"])
    assert "job_a" in store._data
    assert "job_b" in store._data


def test_prune_unknown_jobs_no_op_when_all_known(store: JobStore) -> None:
    removed = prune_unknown_jobs(store, known_job_names=["job_a", "job_b", "job_ghost"])
    assert removed == []
    assert len(store._data) == 3


def test_clear_stale_last_run_clears_old_entry(store: JobStore) -> None:
    old_ts = (datetime.now(tz=timezone.utc) - timedelta(days=120)).isoformat()
    store._data["job_a"]["last_run"] = old_ts
    store._save()

    cleared = clear_stale_last_run(store, ["job_a", "job_b"], max_age_days=90)
    assert cleared == 1
    assert store._data["job_a"]["last_run"] is None


def test_clear_stale_last_run_keeps_recent_entry(store: JobStore) -> None:
    recent_ts = (datetime.now(tz=timezone.utc) - timedelta(days=5)).isoformat()
    store._data["job_a"]["last_run"] = recent_ts
    store._save()

    cleared = clear_stale_last_run(store, ["job_a"], max_age_days=90)
    assert cleared == 0
    assert store._data["job_a"]["last_run"] == recent_ts


def test_clear_stale_last_run_skips_none_last_run(store: JobStore) -> None:
    store._data["job_b"]["last_run"] = None
    cleared = clear_stale_last_run(store, ["job_b"], max_age_days=90)
    assert cleared == 0


def test_run_janitor_combines_results(store: JobStore) -> None:
    old_ts = (datetime.now(tz=timezone.utc) - timedelta(days=200)).isoformat()
    store._data["job_a"]["last_run"] = old_ts
    store._save()

    result = run_janitor(store, known_job_names=["job_a", "job_b"], max_age_days=90)
    assert "job_ghost" in result.jobs_pruned
    assert result.records_cleared == 1


def test_janitor_result_str_nothing() -> None:
    r = JanitorResult(jobs_pruned=[], records_cleared=0)
    assert "nothing" in str(r)


def test_janitor_result_str_with_data() -> None:
    r = JanitorResult(jobs_pruned=["old_job"], records_cleared=2)
    s = str(r)
    assert "old_job" in s
    assert "2" in s
