"""Tests for cronwatcher.backoff."""
from __future__ import annotations

import pytest
from unittest.mock import patch

from cronwatcher.backoff import BackoffPolicy, parse_backoff, resolve_backoff


# ---------------------------------------------------------------------------
# BackoffPolicy.delay
# ---------------------------------------------------------------------------

class TestBackoffDelay:
    def test_attempt_zero_returns_base(self):
        p = BackoffPolicy(base_seconds=30.0, multiplier=2.0, max_seconds=3600.0)
        assert p.delay(0) == pytest.approx(30.0)

    def test_attempt_one_doubles(self):
        p = BackoffPolicy(base_seconds=30.0, multiplier=2.0, max_seconds=3600.0)
        assert p.delay(1) == pytest.approx(60.0)

    def test_attempt_three(self):
        p = BackoffPolicy(base_seconds=10.0, multiplier=3.0, max_seconds=9999.0)
        # 10 * 3^3 = 270
        assert p.delay(3) == pytest.approx(270.0)

    def test_capped_at_max(self):
        p = BackoffPolicy(base_seconds=60.0, multiplier=10.0, max_seconds=100.0)
        assert p.delay(5) == pytest.approx(100.0)

    def test_negative_attempt_treated_as_zero(self):
        p = BackoffPolicy(base_seconds=20.0)
        assert p.delay(-3) == pytest.approx(20.0)

    def test_jitter_returns_value_in_range(self):
        p = BackoffPolicy(base_seconds=60.0, multiplier=2.0, max_seconds=3600.0, jitter=True)
        for _ in range(20):
            d = p.delay(0)
            assert 0.0 <= d <= 60.0

    def test_no_jitter_is_deterministic(self):
        p = BackoffPolicy(base_seconds=60.0, jitter=False)
        assert p.delay(2) == p.delay(2)


# ---------------------------------------------------------------------------
# __str__
# ---------------------------------------------------------------------------

def test_str_contains_key_fields():
    p = BackoffPolicy(base_seconds=45.0, multiplier=3.0, max_seconds=900.0, jitter=True)
    s = str(p)
    assert "45.0" in s
    assert "3.0" in s
    assert "900.0" in s
    assert "jitter=True" in s


# ---------------------------------------------------------------------------
# parse_backoff
# ---------------------------------------------------------------------------

def test_parse_backoff_none_returns_defaults():
    p = parse_backoff(None)
    assert p.base_seconds == 60.0
    assert p.multiplier == 2.0
    assert p.max_seconds == 3600.0
    assert p.jitter is False


def test_parse_backoff_partial_dict():
    p = parse_backoff({"base_seconds": 120.0})
    assert p.base_seconds == 120.0
    assert p.multiplier == 2.0  # default


def test_parse_backoff_full_dict():
    p = parse_backoff({"base_seconds": 5.0, "multiplier": 1.5, "max_seconds": 300.0, "jitter": True})
    assert p.base_seconds == 5.0
    assert p.multiplier == 1.5
    assert p.max_seconds == 300.0
    assert p.jitter is True


# ---------------------------------------------------------------------------
# resolve_backoff
# ---------------------------------------------------------------------------

class _Defaults:
    backoff = {"base_seconds": 90.0, "multiplier": 2.0, "max_seconds": 1800.0}


class _AppConfig:
    defaults = _Defaults()


class _JobWithBackoff:
    backoff = {"base_seconds": 15.0}


class _JobNoBackoff:
    backoff = None


def test_resolve_backoff_uses_job_level():
    p = resolve_backoff(_AppConfig(), _JobWithBackoff())
    assert p.base_seconds == 15.0


def test_resolve_backoff_falls_back_to_global():
    p = resolve_backoff(_AppConfig(), _JobNoBackoff())
    assert p.base_seconds == 90.0


def test_resolve_backoff_no_global_returns_defaults():
    class _MinimalConfig:
        defaults = None

    p = resolve_backoff(_MinimalConfig(), _JobNoBackoff())
    assert p.base_seconds == 60.0  # hardcoded default
