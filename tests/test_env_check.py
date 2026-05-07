"""Tests for cronwatcher.env_check."""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from cronwatcher.config import JobConfig
from cronwatcher.env_check import EnvCheckResult, check_env, check_all_envs


def _job(name: str = "myjob", required_env=None) -> JobConfig:
    return JobConfig(
        name=name,
        command="echo hi",
        schedule="* * * * *",
        required_env=required_env or [],
    )


# ---------------------------------------------------------------------------
# EnvCheckResult helpers
# ---------------------------------------------------------------------------

def test_result_ok_when_no_issues():
    r = EnvCheckResult(job_name="j")
    assert r.ok is True


def test_result_not_ok_when_missing():
    r = EnvCheckResult(job_name="j", missing=["FOO"])
    assert r.ok is False


def test_result_not_ok_when_empty():
    r = EnvCheckResult(job_name="j", empty=["BAR"])
    assert r.ok is False


def test_str_ok():
    r = EnvCheckResult(job_name="myjob")
    assert "OK" in str(r)


def test_str_shows_missing_and_empty():
    r = EnvCheckResult(job_name="j", missing=["A"], empty=["B"])
    s = str(r)
    assert "missing" in s and "A" in s
    assert "empty" in s and "B" in s


# ---------------------------------------------------------------------------
# check_env
# ---------------------------------------------------------------------------

def test_no_required_env_always_ok():
    job = _job(required_env=[])
    result = check_env(job)
    assert result.ok


def test_present_var_is_ok():
    job = _job(required_env=["MY_VAR"])
    with patch.dict(os.environ, {"MY_VAR": "hello"}):
        result = check_env(job)
    assert result.ok


def test_missing_var_reported():
    job = _job(required_env=["MISSING_VAR_XYZ"])
    env = {k: v for k, v in os.environ.items() if k != "MISSING_VAR_XYZ"}
    with patch.dict(os.environ, env, clear=True):
        result = check_env(job)
    assert "MISSING_VAR_XYZ" in result.missing
    assert result.ok is False


def test_empty_var_reported():
    job = _job(required_env=["EMPTY_VAR"])
    with patch.dict(os.environ, {"EMPTY_VAR": "   "}):
        result = check_env(job)
    assert "EMPTY_VAR" in result.empty
    assert result.ok is False


def test_multiple_vars_mixed():
    job = _job(required_env=["GOOD", "BAD_MISSING", "BAD_EMPTY"])
    env_patch = {"GOOD": "yes", "BAD_EMPTY": ""}
    # ensure BAD_MISSING is absent
    base = {k: v for k, v in os.environ.items() if k not in ("GOOD", "BAD_MISSING", "BAD_EMPTY")}
    base.update(env_patch)
    with patch.dict(os.environ, base, clear=True):
        result = check_env(job)
    assert "BAD_MISSING" in result.missing
    assert "BAD_EMPTY" in result.empty
    assert "GOOD" not in result.missing
    assert "GOOD" not in result.empty


# ---------------------------------------------------------------------------
# check_all_envs
# ---------------------------------------------------------------------------

def test_check_all_envs_returns_only_failures():
    ok_job = _job(name="ok", required_env=[])
    bad_job = _job(name="bad", required_env=["__CRONWATCHER_NONEXISTENT__"])
    env = {k: v for k, v in os.environ.items() if k != "__CRONWATCHER_NONEXISTENT__"}
    with patch.dict(os.environ, env, clear=True):
        failures = check_all_envs([ok_job, bad_job])
    assert len(failures) == 1
    assert failures[0].job_name == "bad"


def test_check_all_envs_empty_when_all_ok():
    job = _job(required_env=[])
    assert check_all_envs([job]) == []
