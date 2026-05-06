"""Integration-style tests: retry wired through watcher.Watcher."""
from __future__ import annotations

from unittest.mock import patch, call

import pytest

from cronwatcher.config import AppConfig, JobConfig, AlertConfig
from cronwatcher.job_store import JobStore
from cronwatcher.runner import RunResult
from cronwatcher.watcher import Watcher


def _ok() -> RunResult:
    return RunResult(exit_code=0, stdout="ok", stderr="", duration=0.05)


def _fail() -> RunResult:
    return RunResult(exit_code=1, stdout="", stderr="boom", duration=0.05)


def _make_config(retry_attempts: int = 0, retry_delay: float = 0.0) -> AppConfig:
    job = JobConfig(
        name="j",
        command="echo hi",
        schedule="* * * * *",
        retry_attempts=retry_attempts,
        retry_delay=retry_delay,
    )
    return AppConfig(jobs=[job], alert=AlertConfig())


def _make_store(tmp_path) -> JobStore:
    return JobStore(str(tmp_path / "state.json"))


# ---------------------------------------------------------------------------

def test_watcher_records_success_without_retry(tmp_path):
    cfg = _make_config(retry_attempts=0)
    store = _make_store(tmp_path)
    w = Watcher(cfg, store)

    with patch("cronwatcher.watcher.run_job", return_value=_ok()):
        w.run_job(cfg.jobs[0])

    rec = store.get("j")
    assert rec.last_exit_code == 0
    assert rec.consecutive_failures == 0


def test_watcher_records_failure_without_retry(tmp_path):
    cfg = _make_config(retry_attempts=0)
    store = _make_store(tmp_path)
    w = Watcher(cfg, store)

    with patch("cronwatcher.watcher.run_job", return_value=_fail()):
        w.run_job(cfg.jobs[0])

    rec = store.get("j")
    assert rec.last_exit_code == 1
    assert rec.consecutive_failures == 1


def test_watcher_uses_retry_on_failure(tmp_path):
    """Watcher should call run_with_retry when retry_attempts > 0."""
    cfg = _make_config(retry_attempts=2, retry_delay=0)
    store = _make_store(tmp_path)
    w = Watcher(cfg, store)

    side_effects = [_fail(), _fail(), _ok()]
    with patch("cronwatcher.watcher.run_job", side_effect=side_effects), \
         patch("cronwatcher.retry.run_job", side_effect=side_effects[1:]):
        from cronwatcher.retry import RetryResult
        retry_result = RetryResult(attempts=3, final=_ok(), gave_up=False)
        with patch("cronwatcher.watcher.run_with_retry", return_value=retry_result) as mock_rwr:
            w.run_job(cfg.jobs[0])
            mock_rwr.assert_called_once()

    rec = store.get("j")
    assert rec.last_exit_code == 0
    assert rec.consecutive_failures == 0


def test_watcher_alert_suppressed_when_retry_succeeds(tmp_path):
    """No alert should fire when the job eventually succeeds via retry."""
    cfg = _make_config(retry_attempts=1, retry_delay=0)
    store = _make_store(tmp_path)
    w = Watcher(cfg, store)

    from cronwatcher.retry import RetryResult
    retry_result = RetryResult(attempts=2, final=_ok(), gave_up=False)

    with patch("cronwatcher.watcher.run_with_retry", return_value=retry_result), \
         patch("cronwatcher.watcher.run_job", return_value=_fail()), \
         patch.object(w, "_maybe_alert") as mock_alert:
        w.run_job(cfg.jobs[0])
        mock_alert.assert_not_called()
