"""Tests for cronwatcher.alerter."""

from __future__ import annotations

import smtplib
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.alerter import _build_body, _build_subject, log_alert, send_email_alert
from cronwatcher.config import AlertConfig
from cronwatcher.job_store import JobRecord


@pytest.fixture()
def failing_record() -> JobRecord:
    return JobRecord(
        job_name="backup",
        last_exit_code=1,
        last_run_at="2024-01-15T03:00:00",
        consecutive_failures=3,
        last_stderr="disk full\n",
    )


def test_build_subject(failing_record: JobRecord) -> None:
    assert "backup" in _build_subject(failing_record)
    assert "ALERT" in _build_subject(failing_record)


def test_build_body_contains_fields(failing_record: JobRecord) -> None:
    body = _build_body(failing_record)
    assert "backup" in body
    assert "3" in body
    assert "disk full" in body


def test_build_body_no_stderr() -> None:
    record = JobRecord(job_name="clean", last_exit_code=2, consecutive_failures=1)
    body = _build_body(record)
    assert "stderr" not in body


def test_send_email_no_config(failing_record: JobRecord) -> None:
    cfg = AlertConfig(email=None, on_consecutive_failures=1)
    result = send_email_alert(failing_record, cfg)
    assert result is False


def test_send_email_success(failing_record: JobRecord) -> None:
    cfg = AlertConfig(email="ops@example.com", on_consecutive_failures=1)
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = lambda s: s
    mock_smtp.__exit__ = MagicMock(return_value=False)

    with patch("smtplib.SMTP", return_value=mock_smtp):
        result = send_email_alert(failing_record, cfg)

    assert result is True
    mock_smtp.send_message.assert_called_once()


def test_send_email_smtp_error(failing_record: JobRecord) -> None:
    cfg = AlertConfig(email="ops@example.com", on_consecutive_failures=1)
    with patch("smtplib.SMTP", side_effect=smtplib.SMTPException("conn refused")):
        result = send_email_alert(failing_record, cfg)
    assert result is False


def test_log_alert_does_not_raise(failing_record: JobRecord, caplog) -> None:
    import logging

    with caplog.at_level(logging.WARNING, logger="cronwatcher.alerter"):
        log_alert(failing_record)

    assert "backup" in caplog.text
    assert "3" in caplog.text
