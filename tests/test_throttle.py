"""Tests for cronwatcher.throttle."""

import time
from pathlib import Path

import pytest

from cronwatcher.throttle import Throttler, ThrottleEntry


@pytest.fixture
def throttler(tmp_path: Path) -> Throttler:
    return Throttler(state_path=tmp_path / "throttle.json", cooldown_seconds=600)


# ---------------------------------------------------------------------------
# ThrottleEntry serialisation
# ---------------------------------------------------------------------------

def test_entry_roundtrip():
    entry = ThrottleEntry(job_name="backup", last_alerted_at=1_000_000.0, alert_count=3)
    assert ThrottleEntry.from_dict(entry.to_dict()) == entry


def test_entry_from_dict_defaults():
    entry = ThrottleEntry.from_dict({"job_name": "x", "last_alerted_at": 0.0})
    assert entry.alert_count == 1


# ---------------------------------------------------------------------------
# is_suppressed
# ---------------------------------------------------------------------------

def test_not_suppressed_when_no_entry(throttler: Throttler):
    assert throttler.is_suppressed("new_job") is False


def test_suppressed_within_cooldown(throttler: Throttler):
    now = time.time()
    throttler.record_alert("myjob", now=now)
    assert throttler.is_suppressed("myjob", now=now + 100) is True


def test_not_suppressed_after_cooldown(throttler: Throttler):
    now = time.time()
    throttler.record_alert("myjob", now=now)
    assert throttler.is_suppressed("myjob", now=now + 700) is False


# ---------------------------------------------------------------------------
# record_alert
# ---------------------------------------------------------------------------

def test_record_alert_increments_count(throttler: Throttler):
    now = time.time()
    throttler.record_alert("myjob", now=now)
    throttler.record_alert("myjob", now=now + 700)  # after cooldown
    entry = throttler.get_entry("myjob")
    assert entry is not None
    assert entry.alert_count == 2


def test_record_alert_persists_to_disk(tmp_path: Path):
    path = tmp_path / "throttle.json"
    t1 = Throttler(state_path=path, cooldown_seconds=600)
    t1.record_alert("myjob")

    t2 = Throttler(state_path=path, cooldown_seconds=600)
    assert t2.get_entry("myjob") is not None


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------

def test_reset_clears_entry(throttler: Throttler):
    now = time.time()
    throttler.record_alert("myjob", now=now)
    throttler.reset("myjob")
    assert throttler.is_suppressed("myjob", now=now + 1) is False
    assert throttler.get_entry("myjob") is None


def test_reset_nonexistent_job_is_noop(throttler: Throttler):
    throttler.reset("ghost")  # should not raise


# ---------------------------------------------------------------------------
# Corrupt state file
# ---------------------------------------------------------------------------

def test_corrupt_state_file_is_ignored(tmp_path: Path):
    path = tmp_path / "throttle.json"
    path.write_text("not valid json")
    t = Throttler(state_path=path, cooldown_seconds=60)
    assert t.is_suppressed("any") is False
