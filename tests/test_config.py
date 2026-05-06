"""Tests for cronwatcher.config loading."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from cronwatcher.config import AppConfig, load_config


def write_temp_config(tmp_path: Path, content: str) -> str:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(textwrap.dedent(content))
    return str(cfg)


def test_load_minimal_config(tmp_path):
    path = write_temp_config(tmp_path, """
        jobs:
          - name: ping
            command: echo hello
            schedule: "* * * * *"
    """)
    cfg = load_config(path)
    assert isinstance(cfg, AppConfig)
    assert len(cfg.jobs) == 1
    assert cfg.jobs[0].name == "ping"
    assert cfg.jobs[0].timeout == 60
    assert cfg.jobs[0].notify_channels == ["log"]


def test_load_full_config(tmp_path):
    path = write_temp_config(tmp_path, """
        store_path: /tmp/test.json
        check_interval: 30
        default_notify_channels: [email, log]
        alert:
          smtp_host: smtp.test.com
          smtp_port: 465
          from_address: a@test.com
          to_addresses: [b@test.com]
        jobs:
          - name: backup
            command: /bin/backup
            schedule: "0 1 * * *"
            timeout: 120
            alert_on_failure: true
            notify_channels: [email]
    """)
    cfg = load_config(path)
    assert cfg.store_path == "/tmp/test.json"
    assert cfg.check_interval == 30
    assert cfg.default_notify_channels == ["email", "log"]
    assert cfg.alert.smtp_host == "smtp.test.com"
    assert cfg.alert.smtp_port == 465
    assert cfg.jobs[0].notify_channels == ["email"]


def test_missing_config_file():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/config.yaml")


def test_empty_config_file(tmp_path):
    path = write_temp_config(tmp_path, "")
    cfg = load_config(path)
    assert cfg.jobs == []
    assert cfg.check_interval == 60


def test_job_inherits_default_notify_channels(tmp_path):
    path = write_temp_config(tmp_path, """
        default_notify_channels: [email]
        jobs:
          - name: cleanup
            command: rm -rf /tmp/old
            schedule: "0 4 * * *"
    """)
    cfg = load_config(path)
    assert cfg.jobs[0].notify_channels == ["email"]


def test_to_addresses_string_coerced_to_list(tmp_path):
    path = write_temp_config(tmp_path, """
        alert:
          to_addresses: single@example.com
        jobs: []
    """)
    cfg = load_config(path)
    assert isinstance(cfg.alert.to_addresses, list)
    assert cfg.alert.to_addresses == ["single@example.com"]
