"""Tests for cronwatcher.window."""
from __future__ import annotations

from datetime import datetime, time

import pytest

from cronwatcher.window import (
    TimeWindow,
    WindowPolicy,
    build_window_policy,
    parse_windows,
)


# ---------------------------------------------------------------------------
# TimeWindow.contains
# ---------------------------------------------------------------------------

def test_window_contains_exact_start():
    w = TimeWindow(start=time(9, 0), end=time(17, 0))
    assert w.contains(datetime(2024, 1, 1, 9, 0))


def test_window_excludes_exact_end():
    w = TimeWindow(start=time(9, 0), end=time(17, 0))
    assert not w.contains(datetime(2024, 1, 1, 17, 0))


def test_window_contains_midday():
    w = TimeWindow(start=time(8, 0), end=time(18, 0))
    assert w.contains(datetime(2024, 1, 1, 12, 30))


def test_window_excludes_outside():
    w = TimeWindow(start=time(9, 0), end=time(17, 0))
    assert not w.contains(datetime(2024, 1, 1, 7, 59))


def test_overnight_window_contains_late_hour():
    w = TimeWindow(start=time(22, 0), end=time(6, 0))
    assert w.contains(datetime(2024, 1, 1, 23, 30))


def test_overnight_window_contains_early_hour():
    w = TimeWindow(start=time(22, 0), end=time(6, 0))
    assert w.contains(datetime(2024, 1, 1, 5, 0))


def test_overnight_window_excludes_midday():
    w = TimeWindow(start=time(22, 0), end=time(6, 0))
    assert not w.contains(datetime(2024, 1, 1, 12, 0))


def test_str_representation():
    w = TimeWindow(start=time(9, 0), end=time(17, 30))
    assert str(w) == "09:00-17:30"


# ---------------------------------------------------------------------------
# WindowPolicy
# ---------------------------------------------------------------------------

def test_policy_no_windows_always_allowed():
    p = WindowPolicy(job_name="nightly")
    assert p.is_allowed(datetime(2024, 1, 1, 3, 0))


def test_policy_allowed_within_window():
    p = WindowPolicy(
        job_name="morning",
        windows=[TimeWindow(time(8, 0), time(12, 0))],
    )
    assert p.is_allowed(datetime(2024, 1, 1, 10, 0))


def test_policy_blocked_outside_window():
    p = WindowPolicy(
        job_name="morning",
        windows=[TimeWindow(time(8, 0), time(12, 0))],
    )
    assert not p.is_allowed(datetime(2024, 1, 1, 14, 0))


def test_policy_multiple_windows_second_matches():
    p = WindowPolicy(
        job_name="bi-shift",
        windows=[
            TimeWindow(time(8, 0), time(12, 0)),
            TimeWindow(time(14, 0), time(18, 0)),
        ],
    )
    assert p.is_allowed(datetime(2024, 1, 1, 15, 0))


# ---------------------------------------------------------------------------
# parse_windows / build_window_policy
# ---------------------------------------------------------------------------

def test_parse_windows_basic():
    windows = parse_windows(["09:00-17:00"])
    assert len(windows) == 1
    assert windows[0].start == time(9, 0)
    assert windows[0].end == time(17, 0)


def test_parse_windows_invalid_format():
    with pytest.raises(ValueError, match="Invalid window format"):
        parse_windows(["0900-1700"])


def test_build_window_policy_empty():
    p = build_window_policy("job", [])
    assert p.windows == []
    assert p.is_allowed(datetime(2024, 1, 1, 3, 0))


def test_build_window_policy_with_windows():
    p = build_window_policy("job", ["08:00-20:00"])
    assert len(p.windows) == 1
