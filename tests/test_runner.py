"""Tests for the job runner."""

import pytest

from cronwatcher.config import JobConfig
from cronwatcher.runner import run_job


def make_job(name: str, command: str, timeout: int = 30) -> JobConfig:
    return JobConfig(name=name, command=command, schedule="* * * * *", timeout=timeout)


def test_successful_command():
    job = make_job("echo", "echo hello")
    result = run_job(job)
    assert result.success
    assert result.exit_code == 0
    assert result.stdout == "hello"
    assert result.duration_seconds >= 0


def test_failing_command():
    job = make_job("fail", "exit 42", timeout=5)
    result = run_job(job)
    assert not result.success
    assert result.exit_code == 42


def test_stderr_captured():
    job = make_job("err", "echo oops >&2; exit 1")
    result = run_job(job)
    assert not result.success
    assert "oops" in result.stderr


def test_timeout_returns_minus_one():
    job = make_job("slow", "sleep 10", timeout=1)
    result = run_job(job)
    assert result.exit_code == -1
    assert "timed out" in result.stderr.lower()


def test_result_metadata():
    job = make_job("meta", "true")
    result = run_job(job)
    assert result.job_name == "meta"
    assert result.command == "true"
    assert result.started_at > 0
