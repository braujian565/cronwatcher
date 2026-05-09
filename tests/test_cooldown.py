"""Tests for cronwatcher.cooldown."""

import time
import pytest
from pathlib import Path

from cronwatcher.cooldown import CooldownEntry, CooldownTracker


# ---------------------------------------------------------------------------
# CooldownEntry unit tests
# ---------------------------------------------------------------------------

def test_entry_cooling_down_within_window():
    now = time.time()
    entry = CooldownEntry(job_name="backup", last_run_ts=now - 30, cooldown_seconds=60)
    assert entry.is_cooling_down(now=now) is True


def test_entry_not_cooling_down_after_window():
    now = time.time()
    entry = CooldownEntry(job_name="backup", last_run_ts=now - 120, cooldown_seconds=60)
    assert entry.is_cooling_down(now=now) is False


def test_seconds_remaining_positive_within_window():
    now = time.time()
    entry = CooldownEntry(job_name="backup", last_run_ts=now - 10, cooldown_seconds=60)
    remaining = entry.seconds_remaining(now=now)
    assert 49.0 <= remaining <= 51.0


def test_seconds_remaining_zero_after_window():
    now = time.time()
    entry = CooldownEntry(job_name="backup", last_run_ts=now - 200, cooldown_seconds=60)
    assert entry.seconds_remaining(now=now) == 0.0


def test_entry_roundtrip():
    original = CooldownEntry(job_name="sync", last_run_ts=1_700_000_000.0, cooldown_seconds=300)
    restored = CooldownEntry.from_dict(original.to_dict())
    assert restored.job_name == original.job_name
    assert restored.last_run_ts == original.last_run_ts
    assert restored.cooldown_seconds == original.cooldown_seconds


def test_entry_from_dict_defaults():
    entry = CooldownEntry.from_dict({"job_name": "x"})
    assert entry.last_run_ts == 0.0
    assert entry.cooldown_seconds == 0


# ---------------------------------------------------------------------------
# CooldownTracker integration tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def tracker(tmp_path: Path) -> CooldownTracker:
    return CooldownTracker(tmp_path / "cooldowns.json")


def test_not_cooling_down_when_no_entry(tracker: CooldownTracker):
    assert tracker.is_cooling_down("unknown_job") is False


def test_seconds_remaining_zero_when_no_entry(tracker: CooldownTracker):
    assert tracker.seconds_remaining("unknown_job") == 0.0


def test_record_run_starts_cooldown(tracker: CooldownTracker):
    now = time.time()
    tracker.record_run("myjob", cooldown_seconds=120, now=now)
    assert tracker.is_cooling_down("myjob", now=now + 60) is True


def test_record_run_expires_after_window(tracker: CooldownTracker):
    now = time.time()
    tracker.record_run("myjob", cooldown_seconds=60, now=now)
    assert tracker.is_cooling_down("myjob", now=now + 61) is False


def test_reset_clears_entry(tracker: CooldownTracker):
    now = time.time()
    tracker.record_run("myjob", cooldown_seconds=300, now=now)
    result = tracker.reset("myjob")
    assert result is True
    assert tracker.is_cooling_down("myjob", now=now) is False


def test_reset_returns_false_for_unknown(tracker: CooldownTracker):
    assert tracker.reset("ghost") is False


def test_all_entries_returns_list(tracker: CooldownTracker):
    tracker.record_run("job_a", 60)
    tracker.record_run("job_b", 120)
    names = {e.job_name for e in tracker.all_entries()}
    assert names == {"job_a", "job_b"}


def test_persists_across_instances(tmp_path: Path):
    path = tmp_path / "cooldowns.json"
    now = time.time()
    t1 = CooldownTracker(path)
    t1.record_run("persistent_job", cooldown_seconds=300, now=now)

    t2 = CooldownTracker(path)
    assert t2.is_cooling_down("persistent_job", now=now + 10) is True
