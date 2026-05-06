"""Tests for cronwatcher.snapshots."""

import json
import os
import pytest

from cronwatcher.job_store import JobStore
from cronwatcher.snapshots import (
    JobSnapshot,
    Snapshot,
    diff_snapshots,
    load_snapshot,
    save_snapshot,
    take_snapshot,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def store(tmp_path):
    s = JobStore(str(tmp_path / "jobs.json"))
    return s


def _fill_store(store):
    """Record a success and a failure so the store has real data."""
    store.get_or_create("backup")
    store.record_success("backup", duration=1.2)
    store.get_or_create("cleanup")
    store.record_failure("cleanup", exit_code=1)
    store.record_failure("cleanup", exit_code=1)


# ---------------------------------------------------------------------------
# JobSnapshot serialisation
# ---------------------------------------------------------------------------


def test_job_snapshot_roundtrip():
    snap = JobSnapshot(
        job_name="backup",
        captured_at="2024-01-01T00:00:00+00:00",
        last_exit_code=0,
        consecutive_failures=0,
        last_run_at="2024-01-01T00:00:00+00:00",
    )
    assert JobSnapshot.from_dict(snap.to_dict()) == snap


def test_job_snapshot_missing_optional_fields():
    data = {"job_name": "x", "captured_at": "2024-01-01T00:00:00+00:00"}
    snap = JobSnapshot.from_dict(data)
    assert snap.last_exit_code is None
    assert snap.consecutive_failures == 0
    assert snap.last_run_at is None


# ---------------------------------------------------------------------------
# take_snapshot
# ---------------------------------------------------------------------------


def test_take_snapshot_empty_store(store):
    snap = take_snapshot(store)
    assert snap.jobs == {}
    assert snap.taken_at  # non-empty timestamp


def test_take_snapshot_captures_jobs(store):
    _fill_store(store)
    snap = take_snapshot(store)
    assert "backup" in snap.jobs
    assert "cleanup" in snap.jobs
    assert snap.jobs["backup"].last_exit_code == 0
    assert snap.jobs["cleanup"].consecutive_failures == 2


# ---------------------------------------------------------------------------
# save / load
# ---------------------------------------------------------------------------


def test_save_and_load_snapshot(store, tmp_path):
    _fill_store(store)
    snap = take_snapshot(store)
    path = str(tmp_path / "snap.json")
    save_snapshot(snap, path)

    assert os.path.exists(path)
    loaded = load_snapshot(path)
    assert loaded is not None
    assert loaded.taken_at == snap.taken_at
    assert set(loaded.jobs.keys()) == {"backup", "cleanup"}


def test_load_snapshot_missing_file(tmp_path):
    result = load_snapshot(str(tmp_path / "nonexistent.json"))
    assert result is None


def test_saved_snapshot_is_valid_json(store, tmp_path):
    _fill_store(store)
    snap = take_snapshot(store)
    path = str(tmp_path / "snap.json")
    save_snapshot(snap, path)
    with open(path) as fh:
        data = json.load(fh)
    assert "taken_at" in data
    assert "jobs" in data


# ---------------------------------------------------------------------------
# diff_snapshots
# ---------------------------------------------------------------------------


def _make_snapshot(jobs_data: dict) -> Snapshot:
    snap = Snapshot(taken_at="2024-01-01T00:00:00+00:00")
    for name, kwargs in jobs_data.items():
        snap.jobs[name] = JobSnapshot(
            job_name=name,
            captured_at="2024-01-01T00:00:00+00:00",
            **kwargs,
        )
    return snap


def test_diff_no_changes():
    base = {"job": {"last_exit_code": 0, "consecutive_failures": 0, "last_run_at": None}}
    old = _make_snapshot(base)
    new = _make_snapshot(base)
    assert diff_snapshots(old, new) == []


def test_diff_detects_new_job():
    old = _make_snapshot({})
    new = _make_snapshot({"backup": {"last_exit_code": 0, "consecutive_failures": 0, "last_run_at": None}})
    lines = diff_snapshots(old, new)
    assert any("new job" in l for l in lines)


def test_diff_detects_removed_job():
    old = _make_snapshot({"backup": {"last_exit_code": 0, "consecutive_failures": 0, "last_run_at": None}})
    new = _make_snapshot({})
    lines = diff_snapshots(old, new)
    assert any("removed" in l for l in lines)


def test_diff_detects_failure_increase():
    old = _make_snapshot({"job": {"last_exit_code": 0, "consecutive_failures": 0, "last_run_at": None}})
    new = _make_snapshot({"job": {"last_exit_code": 1, "consecutive_failures": 3, "last_run_at": None}})
    lines = diff_snapshots(old, new)
    assert any("consecutive_failures" in l for l in lines)
    assert any("exit_code" in l for l in lines)
