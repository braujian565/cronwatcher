"""Tests for cronwatcher.runlock."""
from __future__ import annotations

import json
import os
import time

import pytest

from cronwatcher.runlock import LockEntry, RunLock


@pytest.fixture
def lock(tmp_path):
    return RunLock(tmp_path / "locks")


# --- LockEntry ---

def test_lock_entry_roundtrip():
    entry = LockEntry(job_name="backup", pid=1234, started_at=1_000_000.0)
    restored = LockEntry.from_dict(entry.to_dict())
    assert restored.job_name == "backup"
    assert restored.pid == 1234
    assert restored.started_at == 1_000_000.0


def test_lock_entry_from_dict_defaults():
    entry = LockEntry.from_dict({"job_name": "x", "pid": 99})
    assert entry.started_at == 0.0


def test_is_stale_current_process():
    entry = LockEntry(job_name="x", pid=os.getpid())
    assert entry.is_stale() is False


def test_is_stale_dead_pid():
    entry = LockEntry(job_name="x", pid=999_999_999)
    assert entry.is_stale() is True


# --- RunLock ---

def test_acquire_succeeds_when_no_lock(lock):
    assert lock.acquire("myjob") is True


def test_acquire_fails_when_already_locked(lock):
    assert lock.acquire("myjob") is True
    assert lock.acquire("myjob") is False


def test_release_removes_lock(lock):
    lock.acquire("myjob")
    lock.release("myjob")
    assert lock.is_locked("myjob") is False


def test_release_nonexistent_is_safe(lock):
    lock.release("ghost")  # should not raise


def test_is_locked_false_when_no_lock(lock):
    assert lock.is_locked("myjob") is False


def test_is_locked_true_after_acquire(lock):
    lock.acquire("myjob")
    assert lock.is_locked("myjob") is True


def test_stale_lock_cleared_on_acquire(lock, tmp_path):
    # Write a lock file with a dead PID
    stale = LockEntry(job_name="myjob", pid=999_999_999)
    (lock.lock_dir / "myjob.lock").write_text(json.dumps(stale.to_dict()))
    assert lock.acquire("myjob") is True


def test_stale_lock_cleared_on_is_locked(lock):
    stale = LockEntry(job_name="myjob", pid=999_999_999)
    (lock.lock_dir / "myjob.lock").write_text(json.dumps(stale.to_dict()))
    assert lock.is_locked("myjob") is False


def test_corrupt_lock_file_cleared(lock):
    (lock.lock_dir / "myjob.lock").write_text("not json")
    assert lock.acquire("myjob") is True


def test_current_entry_returns_entry(lock):
    lock.acquire("myjob")
    entry = lock.current_entry("myjob")
    assert entry is not None
    assert entry.job_name == "myjob"
    assert entry.pid == os.getpid()


def test_current_entry_returns_none_when_absent(lock):
    assert lock.current_entry("ghost") is None


def test_lock_dir_created_automatically(tmp_path):
    deep = tmp_path / "a" / "b" / "locks"
    rl = RunLock(deep)
    assert deep.exists()
