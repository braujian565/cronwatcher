"""Tests for cronwatcher.history."""

import pytest

from cronwatcher.history import (
    HistoryEntry,
    build_history,
    format_history_table,
    _status,
)
from cronwatcher.job_store import JobRecord, JobStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store(tmp_path):
    return JobStore(str(tmp_path / "test.json"))


# ---------------------------------------------------------------------------
# _status helper
# ---------------------------------------------------------------------------


def test_status_never_run():
    r = JobRecord(job_name="j")
    assert _status(r) == "never_run"


def test_status_ok():
    r = JobRecord(job_name="j", total_runs=3, consecutive_failures=0)
    assert _status(r) == "ok"


def test_status_failing():
    r = JobRecord(job_name="j", total_runs=5, consecutive_failures=2)
    assert _status(r) == "failing"


# ---------------------------------------------------------------------------
# build_history
# ---------------------------------------------------------------------------


def test_build_history_empty_store(store):
    entries = build_history(store)
    assert entries == []


def test_build_history_all_jobs(store):
    store.get("backup")  # creates record
    store.get("cleanup")
    entries = build_history(store)
    assert len(entries) == 2
    assert {e.job_name for e in entries} == {"backup", "cleanup"}


def test_build_history_filtered(store):
    store.get("backup")
    store.get("cleanup")
    entries = build_history(store, job_names=["backup"])
    assert len(entries) == 1
    assert entries[0].job_name == "backup"


def test_build_history_reflects_failures(store):
    record = store.get("nightly")
    record.record_failure(exit_code=1, stderr="boom")
    record.record_failure(exit_code=1, stderr="boom")
    store.save(record)

    entries = build_history(store, job_names=["nightly"])
    assert len(entries) == 1
    e = entries[0]
    assert e.consecutive_failures == 2
    assert e.status == "failing"
    assert e.last_exit_code == 1


def test_build_history_sorted_alphabetically(store):
    for name in ["zebra", "alpha", "middle"]:
        store.get(name)
    entries = build_history(store)
    assert [e.job_name for e in entries] == ["alpha", "middle", "zebra"]


# ---------------------------------------------------------------------------
# format_history_table
# ---------------------------------------------------------------------------


def test_format_history_table_no_entries():
    result = format_history_table([])
    assert result == "No job history available."


def test_format_history_table_contains_headers():
    entry = HistoryEntry(
        job_name="backup",
        last_run="2024-01-01T00:00:00",
        last_exit_code=0,
        consecutive_failures=0,
        total_runs=10,
        status="ok",
    )
    table = format_history_table([entry])
    assert "Job" in table
    assert "Exit Code" in table
    assert "backup" in table
    assert "ok" in table
