"""Tests for cronwatcher.jitter."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cronwatcher.jitter import JitterPolicy, apply_jitter, resolve_jitter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_job(jitter_seconds=None):
    job = MagicMock()
    job.jitter_seconds = jitter_seconds
    return job


# ---------------------------------------------------------------------------
# JitterPolicy
# ---------------------------------------------------------------------------

def test_policy_disabled_when_zero():
    p = JitterPolicy(max_seconds=0)
    assert not p.enabled


def test_policy_enabled_when_positive():
    p = JitterPolicy(max_seconds=30)
    assert p.enabled


def test_str_disabled():
    assert str(JitterPolicy(max_seconds=0)) == "jitter=disabled"


def test_str_enabled():
    assert str(JitterPolicy(max_seconds=15)) == "jitter=0-15s"


def test_sample_zero_when_disabled():
    p = JitterPolicy(max_seconds=0)
    assert p.sample() == 0


def test_sample_within_range():
    p = JitterPolicy(max_seconds=60)
    for _ in range(20):
        s = p.sample()
        assert 0 <= s <= 60


def test_sample_deterministic_with_seed():
    p1 = JitterPolicy(max_seconds=100, seed=42)
    p2 = JitterPolicy(max_seconds=100, seed=42)
    assert p1.sample() == p2.sample()


# ---------------------------------------------------------------------------
# resolve_jitter
# ---------------------------------------------------------------------------

def test_resolve_uses_job_level():
    job = _make_job(jitter_seconds=20)
    policy = resolve_jitter(job, global_max=60)
    assert policy.max_seconds == 20


def test_resolve_falls_back_to_global():
    job = _make_job(jitter_seconds=None)
    policy = resolve_jitter(job, global_max=45)
    assert policy.max_seconds == 45


def test_resolve_disabled_when_no_config():
    job = _make_job(jitter_seconds=None)
    policy = resolve_jitter(job, global_max=None)
    assert not policy.enabled


def test_resolve_job_zero_disables_even_with_global():
    job = _make_job(jitter_seconds=0)
    policy = resolve_jitter(job, global_max=30)
    assert not policy.enabled


# ---------------------------------------------------------------------------
# apply_jitter
# ---------------------------------------------------------------------------

def test_apply_jitter_calls_sleep():
    policy = JitterPolicy(max_seconds=10, seed=7)
    sleep_fn = MagicMock()
    delay = apply_jitter(policy, sleep_fn=sleep_fn)
    assert 0 <= delay <= 10
    if delay > 0:
        sleep_fn.assert_called_once_with(delay)


def test_apply_jitter_no_sleep_when_disabled():
    policy = JitterPolicy(max_seconds=0)
    sleep_fn = MagicMock()
    delay = apply_jitter(policy, sleep_fn=sleep_fn)
    assert delay == 0
    sleep_fn.assert_not_called()
