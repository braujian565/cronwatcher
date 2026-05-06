"""Tests for cronwatcher.digest."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.config import AlertConfig, AppConfig, JobConfig
from cronwatcher.digest import DigestReport, build_digest, send_digest
from cronwatcher.job_store import JobStore


@pytest.fixture()
def store(tmp_path):
    return JobStore(str(tmp_path / "state.json"))


@pytest.fixture()
def app_config(tmp_path):
    return AppConfig(
        jobs=[
            JobConfig(name="backup", command="tar czf /tmp/b.tgz /etc", schedule="0 2 * * *"),
            JobConfig(name="cleanup", command="rm -rf /tmp/old", schedule="30 3 * * *"),
        ],
        alert=AlertConfig(),
        state_file=str(tmp_path / "state.json"),
        check_interval=60,
    )


def test_build_digest_empty_store(app_config, store):
    report = build_digest(app_config, store)
    assert report.total_jobs == 2
    assert report.never_run_count == 2
    assert report.ok_count == 0
    assert report.failing_count == 0


def test_build_digest_with_ok_job(app_config, store):
    rec = store.get("backup")
    store.record_success("backup", 0)
    report = build_digest(app_config, store)
    assert report.ok_count == 1
    assert report.never_run_count == 1


def test_build_digest_with_failing_job(app_config, store):
    store.record_failure("cleanup", 1, "error")
    report = build_digest(app_config, store)
    assert report.failing_count == 1


def test_summary_line(app_config, store):
    report = build_digest(app_config, store)
    line = report.summary_line()
    assert "2 jobs" in line
    assert "never run" in line


def test_digest_table_non_empty(app_config, store):
    report = build_digest(app_config, store)
    assert "backup" in report.table
    assert "cleanup" in report.table


def test_send_digest_calls_channels(app_config, store):
    fake_handler = MagicMock()
    with patch("cronwatcher.digest.get_channels", return_value={"fake": fake_handler}):
        send_digest(app_config, store)
    fake_handler.assert_called_once()
    call_args = fake_handler.call_args
    subject = call_args[0][0]
    assert "cronwatcher" in subject
    assert "Daily digest" in subject


def test_send_digest_dry_run_not_called(app_config, store):
    """send_digest itself always sends; dry-run is a CLI concern."""
    fake_handler = MagicMock()
    with patch("cronwatcher.digest.get_channels", return_value={"fake": fake_handler}):
        send_digest(app_config, store)
    assert fake_handler.call_count == 1
