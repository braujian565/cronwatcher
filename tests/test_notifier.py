"""Tests for cronwatcher.notifier dispatch/registry."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.config import AlertConfig
from cronwatcher.job_store import JobRecord
from cronwatcher import notifier


@pytest.fixture()
def record() -> JobRecord:
    r = JobRecord(job_name="test-job")
    r.consecutive_failures = 2
    r.last_exit_code = 1
    r.last_stderr = "something went wrong"
    return r


@pytest.fixture()
def alert_cfg() -> AlertConfig:
    return AlertConfig(
        smtp_host="localhost",
        from_address="a@b.com",
        to_addresses=["ops@b.com"],
    )


def test_get_channels_includes_builtins():
    channels = notifier.get_channels()
    assert "email" in channels
    assert "log" in channels


def test_register_adds_custom_channel():
    @notifier.register("slack")
    def _slack(rec, cfg):  # noqa: ARG001
        pass

    assert "slack" in notifier.get_channels()
    # clean up
    del notifier._REGISTRY["slack"]


def test_dispatch_calls_log_handler(record, alert_cfg):
    with patch("cronwatcher.notifier.log_alert") as mock_log:
        notifier.dispatch(record, alert_cfg, channels=["log"])
        mock_log.assert_called_once_with(record)


def test_dispatch_calls_email_handler(record, alert_cfg):
    with patch("cronwatcher.notifier.send_email_alert") as mock_email:
        notifier.dispatch(record, alert_cfg, channels=["email"])
        mock_email.assert_called_once_with(record, alert_cfg)


def test_dispatch_multiple_channels(record, alert_cfg):
    with patch("cronwatcher.notifier.log_alert") as mock_log, \
         patch("cronwatcher.notifier.send_email_alert") as mock_email:
        notifier.dispatch(record, alert_cfg, channels=["log", "email"])
        mock_log.assert_called_once()
        mock_email.assert_called_once()


def test_dispatch_unknown_channel_logs_warning(record, alert_cfg, caplog):
    with caplog.at_level(logging.WARNING, logger="cronwatcher.notifier"):
        notifier.dispatch(record, alert_cfg, channels=["nonexistent"])
    assert "nonexistent" in caplog.text


def test_dispatch_handler_exception_does_not_propagate(record, alert_cfg):
    @notifier.register("broken")
    def _broken(rec, cfg):  # noqa: ARG001
        raise RuntimeError("boom")

    # Should not raise
    notifier.dispatch(record, alert_cfg, channels=["broken"])
    del notifier._REGISTRY["broken"]


def test_dispatch_handler_exception_logs_error(record, alert_cfg, caplog):
    """Verify that a handler exception is logged at ERROR level with context."""
    @notifier.register("error_prone")
    def _error_prone(rec, cfg):  # noqa: ARG001
        raise ValueError("unexpected value")

    with caplog.at_level(logging.ERROR, logger="cronwatcher.notifier"):
        notifier.dispatch(record, alert_cfg, channels=["error_prone"])

    assert "error_prone" in caplog.text
    del notifier._REGISTRY["error_prone"]
