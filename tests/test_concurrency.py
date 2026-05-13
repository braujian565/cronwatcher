"""Tests for cronwatcher.concurrency."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwatcher.concurrency import ConcurrencyLimit, ConcurrencyManager


@pytest.fixture()
def mgr(tmp_path: Path) -> ConcurrencyManager:
    return ConcurrencyManager(store_path=tmp_path / "concurrency.json")


# ---------------------------------------------------------------------------
# ConcurrencyLimit unit tests
# ---------------------------------------------------------------------------

def test_limit_available_when_below_max() -> None:
    lim = ConcurrencyLimit(name="grp", max_running=2)
    assert lim.available() is True


def test_limit_unavailable_when_at_max() -> None:
    lim = ConcurrencyLimit(name="grp", max_running=1, running=["job_a"])
    assert lim.available() is False


def test_acquire_adds_job_name() -> None:
    lim = ConcurrencyLimit(name="grp", max_running=3)
    ok = lim.acquire("job_a")
    assert ok is True
    assert "job_a" in lim.running


def test_acquire_fails_when_full() -> None:
    lim = ConcurrencyLimit(name="grp", max_running=1, running=["job_a"])
    ok = lim.acquire("job_b")
    assert ok is False
    assert "job_b" not in lim.running


def test_release_removes_job_name() -> None:
    lim = ConcurrencyLimit(name="grp", max_running=2, running=["job_a"])
    lim.release("job_a")
    assert "job_a" not in lim.running


def test_roundtrip() -> None:
    lim = ConcurrencyLimit(name="grp", max_running=4, running=["job_x"])
    assert ConcurrencyLimit.from_dict(lim.to_dict()) == lim


# ---------------------------------------------------------------------------
# ConcurrencyManager tests
# ---------------------------------------------------------------------------

def test_set_limit_persists(mgr: ConcurrencyManager, tmp_path: Path) -> None:
    mgr.set_limit("batch", 3)
    raw = json.loads((tmp_path / "concurrency.json").read_text())
    assert "batch" in raw
    assert raw["batch"]["max_running"] == 3


def test_acquire_succeeds_when_no_limit(mgr: ConcurrencyManager) -> None:
    # No limit configured → always allow
    assert mgr.acquire("unknown", "job_a") is True


def test_acquire_succeeds_within_limit(mgr: ConcurrencyManager) -> None:
    mgr.set_limit("batch", 2)
    assert mgr.acquire("batch", "job_a") is True
    assert mgr.acquire("batch", "job_b") is True


def test_acquire_blocked_at_limit(mgr: ConcurrencyManager) -> None:
    mgr.set_limit("batch", 1)
    mgr.acquire("batch", "job_a")
    assert mgr.acquire("batch", "job_b") is False


def test_release_frees_slot(mgr: ConcurrencyManager) -> None:
    mgr.set_limit("batch", 1)
    mgr.acquire("batch", "job_a")
    mgr.release("batch", "job_a")
    assert mgr.acquire("batch", "job_b") is True


def test_remove_deletes_limit(mgr: ConcurrencyManager) -> None:
    mgr.set_limit("batch", 2)
    removed = mgr.remove("batch")
    assert removed is True
    assert mgr.get_limit("batch") is None


def test_remove_nonexistent_returns_false(mgr: ConcurrencyManager) -> None:
    assert mgr.remove("ghost") is False


def test_persistence_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "concurrency.json"
    mgr1 = ConcurrencyManager(store_path=path)
    mgr1.set_limit("etl", 5)
    mgr1.acquire("etl", "job_x")

    mgr2 = ConcurrencyManager(store_path=path)
    lim = mgr2.get_limit("etl")
    assert lim is not None
    assert lim.max_running == 5
    assert "job_x" in lim.running
