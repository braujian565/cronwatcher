"""Tests for cronwatcher.retry."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from cronwatcher.config import JobConfig
from cronwatcher.runner import RunResult
from cronwatcher.retry import RetryResult, should_retry, run_with_retry


def make_job(name="test", cmd="echo hi", retry_attempts=0, retry_delay=0) -> JobConfig:
    return JobConfig(
        name=name,
        command=cmd,
        schedule="* * * * *",
        retry_attempts=retry_attempts,
        retry_delay=retry_delay,
    )


def ok_result() -> RunResult:
    return RunResult(exit_code=0, stdout="ok", stderr="", duration=0.1)


def fail_result() -> RunResult:
    return RunResult(exit_code=1, stdout="", stderr="err", duration=0.1)


# ---------------------------------------------------------------------------
# should_retry
# ---------------------------------------------------------------------------

def test_should_retry_false_when_zero():
    assert should_retry(make_job(retry_attempts=0)) is False


def test_should_retry_false_when_none():
    job = make_job()
    job.retry_attempts = None
    assert should_retry(job) is False


def test_should_retry_true_when_positive():
    assert should_retry(make_job(retry_attempts=3)) is True


# ---------------------------------------------------------------------------
# run_with_retry
# ---------------------------------------------------------------------------

def test_no_retry_on_success():
    job = make_job(retry_attempts=3)
    result = run_with_retry(job, first_result=ok_result(), _sleep=lambda _: None)
    assert result.attempts == 1
    assert result.succeeded is True
    assert result.gave_up is False


def test_retries_until_success():
    job = make_job(retry_attempts=3)
    side_effects = [fail_result(), fail_result(), ok_result()]
    with patch("cronwatcher.retry.run_job", side_effect=side_effects):
        result = run_with_retry(job, first_result=fail_result(), _sleep=lambda _: None)
    # first_result counts as attempt 1; then 3 more calls → attempt 4 succeeds
    assert result.succeeded is True
    assert result.attempts == 4
    assert result.gave_up is False


def test_gives_up_after_max_retries():
    job = make_job(retry_attempts=2)
    with patch("cronwatcher.retry.run_job", return_value=fail_result()):
        result = run_with_retry(job, first_result=fail_result(), _sleep=lambda _: None)
    assert result.gave_up is True
    assert result.attempts == 3   # 1 initial + 2 retries


def test_sleep_called_with_delay():
    job = make_job(retry_attempts=1, retry_delay=5)
    sleep_mock = MagicMock()
    with patch("cronwatcher.retry.run_job", return_value=ok_result()):
        run_with_retry(job, first_result=fail_result(), _sleep=sleep_mock)
    sleep_mock.assert_called_once_with(5.0)


def test_no_sleep_when_delay_zero():
    job = make_job(retry_attempts=2, retry_delay=0)
    sleep_mock = MagicMock()
    with patch("cronwatcher.retry.run_job", return_value=ok_result()):
        run_with_retry(job, first_result=fail_result(), _sleep=sleep_mock)
    sleep_mock.assert_not_called()


def test_retry_result_succeeded_property():
    r = RetryResult(attempts=1, final=ok_result(), gave_up=False)
    assert r.succeeded is True
    r2 = RetryResult(attempts=3, final=fail_result(), gave_up=True)
    assert r2.succeeded is False
