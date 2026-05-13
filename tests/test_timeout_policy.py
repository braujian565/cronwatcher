"""Tests for cronwatcher.timeout_policy."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cronwatcher.timeout_policy import (
    TimeoutPolicy,
    resolve_all_timeouts,
    resolve_timeout,
    _HARD_DEFAULT_SECONDS,
)


def _make_job(name: str = "backup", timeout: int | None = None) -> MagicMock:
    job = MagicMock()
    job.name = name
    job.timeout = timeout
    return job


def _make_app_config(
    jobs: list | None = None,
    default_timeout: int | None = None,
) -> MagicMock:
    cfg = MagicMock()
    cfg.jobs = jobs or []
    cfg.default_timeout = default_timeout
    return cfg


# ---------------------------------------------------------------------------
# TimeoutPolicy.__str__
# ---------------------------------------------------------------------------

def test_str_representation():
    policy = TimeoutPolicy(job_name="sync", timeout_seconds=30, source="job")
    assert "sync" in str(policy)
    assert "30" in str(policy)
    assert "job" in str(policy)


# ---------------------------------------------------------------------------
# resolve_timeout – source precedence
# ---------------------------------------------------------------------------

def test_job_level_timeout_takes_priority():
    job = _make_job(timeout=45)
    cfg = _make_app_config(default_timeout=120)
    policy = resolve_timeout(job, cfg)
    assert policy.timeout_seconds == 45
    assert policy.source == "job"


def test_global_timeout_used_when_job_has_none():
    job = _make_job(timeout=None)
    cfg = _make_app_config(default_timeout=90)
    policy = resolve_timeout(job, cfg)
    assert policy.timeout_seconds == 90
    assert policy.source == "global"


def test_hard_default_used_when_both_absent():
    job = _make_job(timeout=None)
    cfg = _make_app_config(default_timeout=None)
    policy = resolve_timeout(job, cfg)
    assert policy.timeout_seconds == _HARD_DEFAULT_SECONDS
    assert policy.source == "default"


def test_zero_job_timeout_falls_back_to_global():
    """A timeout of 0 is treated as 'not set'."""
    job = _make_job(timeout=0)
    cfg = _make_app_config(default_timeout=30)
    policy = resolve_timeout(job, cfg)
    assert policy.timeout_seconds == 30
    assert policy.source == "global"


def test_zero_global_timeout_falls_back_to_default():
    job = _make_job(timeout=0)
    cfg = _make_app_config(default_timeout=0)
    policy = resolve_timeout(job, cfg)
    assert policy.timeout_seconds == _HARD_DEFAULT_SECONDS
    assert policy.source == "default"


def test_job_name_preserved():
    job = _make_job(name="nightly-report", timeout=10)
    cfg = _make_app_config()
    policy = resolve_timeout(job, cfg)
    assert policy.job_name == "nightly-report"


# ---------------------------------------------------------------------------
# resolve_all_timeouts
# ---------------------------------------------------------------------------

def test_resolve_all_returns_one_per_job():
    jobs = [_make_job("a", 10), _make_job("b", None), _make_job("c", 0)]
    cfg = _make_app_config(jobs=jobs, default_timeout=20)
    policies = resolve_all_timeouts(cfg)
    assert len(policies) == 3


def test_resolve_all_empty_jobs():
    cfg = _make_app_config(jobs=[], default_timeout=30)
    assert resolve_all_timeouts(cfg) == []
