"""Tests for cronwatcher.trend."""
from __future__ import annotations

import pytest

from cronwatcher.trend import (
    TrendReport,
    _failure_rate,
    check_all_trends,
    compute_trend,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeRecord:
    def __init__(self, history):
        self.history = history


class _FakeStore:
    def __init__(self, records: dict):
        self._records = records

    def get(self, job_name):
        return self._records.get(job_name)


def _runs(*successes: bool):
    """Build minimal history dicts from a sequence of success flags."""
    return [{"success": s} for s in successes]


# ---------------------------------------------------------------------------
# _failure_rate
# ---------------------------------------------------------------------------

def test_failure_rate_empty():
    assert _failure_rate([]) == 0.0


def test_failure_rate_all_failures():
    assert _failure_rate([True, True, True]) == pytest.approx(1.0)


def test_failure_rate_mixed():
    assert _failure_rate([True, False, True, False]) == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# compute_trend – not enough data
# ---------------------------------------------------------------------------

def test_compute_trend_returns_none_when_no_record():
    store = _FakeStore({})
    assert compute_trend("backup", store) is None


def test_compute_trend_returns_none_when_fewer_than_4_runs():
    store = _FakeStore({"backup": _FakeRecord(_runs(True, False, True))})
    assert compute_trend("backup", store) is None


# ---------------------------------------------------------------------------
# compute_trend – direction detection
# ---------------------------------------------------------------------------

def test_compute_trend_worsening():
    # Earlier half: all success; recent half: all failure
    runs = _runs(True, True, True, True, False, False, False, False)
    store = _FakeStore({"job": _FakeRecord(runs)})
    report = compute_trend("job", store, window=8)
    assert report is not None
    assert report.direction == "worsening"
    assert report.delta > 0


def test_compute_trend_improving():
    # Earlier half: all failure; recent half: all success
    runs = _runs(False, False, False, False, True, True, True, True)
    store = _FakeStore({"job": _FakeRecord(runs)})
    report = compute_trend("job", store, window=8)
    assert report is not None
    assert report.direction == "improving"
    assert report.delta < 0


def test_compute_trend_stable():
    # Uniform 50 % failure throughout
    runs = _runs(True, False, True, False, True, False, True, False)
    store = _FakeStore({"job": _FakeRecord(runs)})
    report = compute_trend("job", store, window=8, stable_threshold=0.05)
    assert report is not None
    assert report.direction == "stable"


def test_compute_trend_uses_last_window_runs():
    # Prepend 100 failures; the last 8 runs are all successes → improving
    old_runs = _runs(*([False] * 100))
    recent_runs = _runs(*([True] * 8))
    store = _FakeStore({"job": _FakeRecord(old_runs + recent_runs)})
    report = compute_trend("job", store, window=8)
    assert report is not None
    assert report.window_size == 8
    assert report.direction == "stable"  # both halves are 0 % failure


# ---------------------------------------------------------------------------
# TrendReport.__str__
# ---------------------------------------------------------------------------

def test_str_worsening():
    r = TrendReport("myjob", 10, 0.6, 0.2, "worsening", 0.4)
    text = str(r)
    assert "worsening" in text
    assert "↑" in text
    assert "myjob" in text


def test_str_improving():
    r = TrendReport("myjob", 10, 0.1, 0.5, "improving", -0.4)
    assert "↓" in str(r)


def test_str_stable():
    r = TrendReport("myjob", 10, 0.3, 0.3, "stable", 0.0)
    assert "→" in str(r)


# ---------------------------------------------------------------------------
# check_all_trends
# ---------------------------------------------------------------------------

def test_check_all_trends_skips_jobs_without_data():
    store = _FakeStore({
        "good_job": _FakeRecord(_runs(True, True, True, True, True, True, True, True)),
        "no_data": _FakeRecord(_runs(True)),
    })
    reports = check_all_trends(store, ["good_job", "no_data", "missing"])
    assert len(reports) == 1
    assert reports[0].job_name == "good_job"


def test_check_all_trends_empty_job_list():
    store = _FakeStore({})
    assert check_all_trends(store, []) == []
