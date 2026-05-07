"""Integration tests for watcher_hooks_integration.run_job_with_hooks."""
import pytest
from unittest.mock import patch, MagicMock

from cronwatcher.runner import RunResult
from cronwatcher.watcher_hooks_integration import run_job_with_hooks


def _make_job(pre_hooks=None, post_hooks=None, command="echo ok"):
    job = MagicMock()
    job.name = "test_job"
    job.command = command
    job.pre_hooks = pre_hooks or []
    job.post_hooks = post_hooks or []
    return job


_OK_RESULT = RunResult(returncode=0, stdout="ok", stderr="", duration_seconds=0.1)
_FAIL_RESULT = RunResult(returncode=1, stdout="", stderr="err", duration_seconds=0.1)


# ---------------------------------------------------------------------------
# No hooks — delegates straight to run_job
# ---------------------------------------------------------------------------

def test_no_hooks_runs_job():
    job = _make_job()
    with patch("cronwatcher.watcher_hooks_integration.run_job",
               return_value=_OK_RESULT) as mock_run:
        result = run_job_with_hooks(job)
    mock_run.assert_called_once_with(job)
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# Pre-hook passes → job runs
# ---------------------------------------------------------------------------

def test_passing_pre_hook_allows_job():
    job = _make_job(pre_hooks=["echo pre"])
    with patch("cronwatcher.watcher_hooks_integration.run_job",
               return_value=_OK_RESULT) as mock_run:
        result = run_job_with_hooks(job)
    mock_run.assert_called_once_with(job)
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# Pre-hook fails → job is skipped, returncode -2
# ---------------------------------------------------------------------------

def test_failing_pre_hook_skips_job():
    job = _make_job(pre_hooks=["exit 1"])
    with patch("cronwatcher.watcher_hooks_integration.run_job") as mock_run:
        result = run_job_with_hooks(job)
    mock_run.assert_not_called()
    assert result.returncode == -2
    assert "pre-hook failed" in result.stderr


# ---------------------------------------------------------------------------
# Post-hook runs after successful job
# ---------------------------------------------------------------------------

def test_post_hook_runs_after_job():
    job = _make_job(post_hooks=["echo post"])
    with patch("cronwatcher.watcher_hooks_integration.run_job",
               return_value=_OK_RESULT):
        with patch("cronwatcher.watcher_hooks_integration.run_post_hooks") as mock_post:
            result = run_job_with_hooks(job)
    mock_post.assert_called_once_with(["echo post"], timeout=30)
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# Post-hook failure does NOT change job result
# ---------------------------------------------------------------------------

def test_failing_post_hook_does_not_change_result():
    job = _make_job(post_hooks=["exit 99"])
    with patch("cronwatcher.watcher_hooks_integration.run_job",
               return_value=_OK_RESULT):
        result = run_job_with_hooks(job)
    # Job result is still the successful one
    assert result.returncode == 0
