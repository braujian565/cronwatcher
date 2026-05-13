"""Tests for cronwatcher.variance."""
from __future__ import annotations

import math
import pytest
from unittest.mock import MagicMock

from cronwatcher.variance import (
    VarianceReport,
    _std_dev,
    compute_variance,
    check_all_variances,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_store(histories: dict[str, list[float]]) -> MagicMock:
    """Build a minimal mock JobStore with per-job duration histories."""
    store = MagicMock()

    def _get(name):
        rec = MagicMock()
        rec.history = [{"duration": d} for d in histories.get(name, [])]
        return rec

    store.get.side_effect = _get
    store.all_jobs.return_value = list(histories.keys())
    return store


# ---------------------------------------------------------------------------
# _std_dev
# ---------------------------------------------------------------------------

def test_std_dev_single_value():
    assert _std_dev([5.0], 5.0) == 0.0


def test_std_dev_two_equal_values():
    assert _std_dev([3.0, 3.0], 3.0) == 0.0


def test_std_dev_known_values():
    # population std of [2, 4, 4, 4, 5, 5, 7, 9] == 2.0
    data = [2, 4, 4, 4, 5, 5, 7, 9]
    mean = sum(data) / len(data)
    result = _std_dev([float(x) for x in data], mean)
    assert abs(result - 2.0) < 1e-9


# ---------------------------------------------------------------------------
# compute_variance
# ---------------------------------------------------------------------------

def test_no_history_returns_nones():
    store = _make_store({"backup": []})
    r = compute_variance("backup", store)
    assert r.avg_duration is None
    assert r.std_dev is None
    assert r.last_duration is None
    assert r.z_score is None
    assert r.flagged is False


def test_single_run_zero_std_dev():
    store = _make_store({"nightly": [10.0]})
    r = compute_variance("nightly", store)
    assert r.avg_duration == 10.0
    assert r.std_dev == 0.0
    assert r.last_duration == 10.0
    assert r.z_score == 0.0
    assert r.flagged is False


def test_normal_run_not_flagged():
    durations = [10.0, 10.5, 9.8, 10.2, 10.1]
    store = _make_store({"job": durations})
    r = compute_variance("job", store, threshold_z=2.0)
    assert r.flagged is False


def test_outlier_run_is_flagged():
    # last run is 100s, rest ~10s
    durations = [10.0, 10.0, 10.0, 10.0, 100.0]
    store = _make_store({"slow": durations})
    r = compute_variance("slow", store, threshold_z=2.0)
    assert r.flagged is True
    assert r.z_score is not None and r.z_score > 2.0


def test_str_no_history():
    r = VarianceReport("myjob", None, None, None, None)
    assert "no runtime history" in str(r)


def test_str_flagged_contains_marker():
    r = VarianceReport("myjob", 10.0, 2.0, 20.0, 5.0, flagged=True)
    assert "[FLAGGED]" in str(r)


# ---------------------------------------------------------------------------
# check_all_variances
# ---------------------------------------------------------------------------

def test_check_all_empty_store():
    store = _make_store({})
    reports = check_all_variances(store)
    assert reports == []


def test_check_all_returns_one_per_job():
    store = _make_store({"a": [1.0, 2.0], "b": [5.0, 6.0, 5.5]})
    reports = check_all_variances(store)
    assert len(reports) == 2
    names = {r.job_name for r in reports}
    assert names == {"a", "b"}


def test_check_all_sorted_by_name():
    store = _make_store({"zebra": [1.0], "alpha": [2.0]})
    reports = check_all_variances(store)
    assert [r.job_name for r in reports] == ["alpha", "zebra"]
