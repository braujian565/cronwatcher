"""Tests for cronwatcher.ratelimit."""
import time
import pytest
from pathlib import Path
from cronwatcher.ratelimit import RateLimitEntry, RateLimiter


@pytest.fixture
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "ratelimit.json"


@pytest.fixture
def limiter(store_path: Path) -> RateLimiter:
    return RateLimiter(store_path, window_seconds=60.0, max_alerts=3)


def test_entry_roundtrip():
    entry = RateLimitEntry(job_name="backup", timestamps=[1000.0, 2000.0])
    assert RateLimitEntry.from_dict(entry.to_dict()) == entry


def test_entry_from_dict_defaults():
    entry = RateLimitEntry.from_dict({"job_name": "x"})
    assert entry.timestamps == []


def test_prune_removes_old_timestamps():
    now = time.time()
    entry = RateLimitEntry(job_name="j", timestamps=[now - 120, now - 30, now - 10])
    entry.prune(window_seconds=60.0, now=now)
    assert len(entry.timestamps) == 2


def test_count_in_window(store_path):
    now = time.time()
    limiter = RateLimiter(store_path, window_seconds=60.0, max_alerts=5)
    limiter.record_alert("job1", now=now - 90)
    limiter.record_alert("job1", now=now - 30)
    limiter.record_alert("job1", now=now - 10)
    entry = limiter._entry("job1")
    assert entry.count_in_window(60.0, now=now) == 2


def test_not_limited_initially(limiter):
    assert not limiter.is_limited("new_job")


def test_limited_after_max_alerts(limiter):
    now = time.time()
    for i in range(3):
        limiter.record_alert("job1", now=now - i)
    assert limiter.is_limited("job1", now=now)


def test_not_limited_after_window_expires(store_path):
    limiter = RateLimiter(store_path, window_seconds=60.0, max_alerts=3)
    past = time.time() - 120
    for i in range(3):
        limiter.record_alert("job1", now=past + i)
    assert not limiter.is_limited("job1", now=time.time())


def test_reset_clears_history(limiter):
    now = time.time()
    for i in range(3):
        limiter.record_alert("job1", now=now - i)
    limiter.reset("job1")
    assert not limiter.is_limited("job1", now=now)


def test_persists_across_instances(store_path):
    now = time.time()
    l1 = RateLimiter(store_path, window_seconds=60.0, max_alerts=3)
    for i in range(3):
        l1.record_alert("job1", now=now - i)
    l2 = RateLimiter(store_path, window_seconds=60.0, max_alerts=3)
    assert l2.is_limited("job1", now=now)


def test_all_entries(limiter):
    limiter.record_alert("a")
    limiter.record_alert("b")
    names = {e.job_name for e in limiter.all_entries()}
    assert names == {"a", "b"}
