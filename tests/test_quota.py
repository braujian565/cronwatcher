"""Tests for cronwatcher.quota."""
from __future__ import annotations

import time
import pytest

from cronwatcher.quota import QuotaEntry, QuotaManager


# ---------------------------------------------------------------------------
# QuotaEntry unit tests
# ---------------------------------------------------------------------------

def test_entry_roundtrip():
    e = QuotaEntry("backup", max_runs=5, window_seconds=3600, timestamps=[1.0, 2.0])
    assert QuotaEntry.from_dict(e.to_dict()) == e


def test_entry_from_dict_defaults():
    e = QuotaEntry.from_dict({"job_name": "x", "max_runs": 3, "window_seconds": 60})
    assert e.timestamps == []


def test_prune_removes_old_timestamps():
    now = time.time()
    e = QuotaEntry("j", 10, 60, timestamps=[now - 120, now - 30, now])
    e.prune(now)
    assert len(e.timestamps) == 2


def test_count_in_window_excludes_old():
    now = time.time()
    e = QuotaEntry("j", 10, 60, timestamps=[now - 200, now - 10, now])
    assert e.count_in_window(now) == 2


def test_is_exceeded_false_below_max():
    now = time.time()
    e = QuotaEntry("j", 3, 60, timestamps=[now - 10, now - 5])
    assert not e.is_exceeded(now)


def test_is_exceeded_true_at_max():
    now = time.time()
    e = QuotaEntry("j", 2, 60, timestamps=[now - 10, now - 5])
    assert e.is_exceeded(now)


def test_record_run_appends_timestamp():
    now = time.time()
    e = QuotaEntry("j", 5, 60)
    e.record_run(now)
    assert len(e.timestamps) == 1
    assert e.timestamps[0] == now


# ---------------------------------------------------------------------------
# QuotaManager integration tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def mgr(tmp_path):
    return QuotaManager(store_path=str(tmp_path / "quotas.json"))


def test_no_entry_is_not_exceeded(mgr):
    assert not mgr.is_exceeded("unknown_job")


def test_set_and_retrieve_quota(mgr):
    mgr.set_quota("backup", max_runs=3, window_seconds=3600)
    entry = mgr.get_entry("backup")
    assert entry is not None
    assert entry.max_runs == 3
    assert entry.window_seconds == 3600


def test_record_run_increments_count(mgr):
    mgr.set_quota("backup", 5, 3600)
    mgr.record_run("backup")
    mgr.record_run("backup")
    assert mgr.get_entry("backup").count_in_window() == 2


def test_exceeded_after_max_runs(mgr):
    mgr.set_quota("job", 2, 3600)
    mgr.record_run("job")
    mgr.record_run("job")
    assert mgr.is_exceeded("job")


def test_persistence_across_instances(tmp_path):
    path = str(tmp_path / "quotas.json")
    m1 = QuotaManager(store_path=path)
    m1.set_quota("sync", 10, 86400)
    m1.record_run("sync")

    m2 = QuotaManager(store_path=path)
    assert m2.get_entry("sync") is not None
    assert m2.get_entry("sync").count_in_window() == 1


def test_remove_entry(mgr):
    mgr.set_quota("old_job", 1, 60)
    assert mgr.remove("old_job") is True
    assert mgr.get_entry("old_job") is None


def test_remove_missing_returns_false(mgr):
    assert mgr.remove("ghost") is False


def test_all_entries_returns_list(mgr):
    mgr.set_quota("a", 1, 60)
    mgr.set_quota("b", 2, 120)
    names = {e.job_name for e in mgr.all_entries()}
    assert names == {"a", "b"}
