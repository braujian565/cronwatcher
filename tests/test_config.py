"""Tests for cronwatcher configuration loader."""

import os
import pytest
import tempfile
import yaml

from cronwatcher.config import load_config, AppConfig, JobConfig, AlertConfig


MINIMAL_CONFIG = {
    "jobs": [
        {"name": "test_job", "schedule": "* * * * *"}
    ]
}

FULL_CONFIG = {
    "log_level": "DEBUG",
    "log_file": "/tmp/test.log",
    "state_dir": "/tmp/cronwatcher",
    "alerts": {
        "email": "admin@example.com",
        "webhook_url": "https://hooks.example.com/alert",
        "slack_channel": "#alerts",
    },
    "jobs": [
        {
            "name": "backup",
            "schedule": "0 2 * * *",
            "timeout": 3600,
            "alert_on_failure": True,
            "alert_on_timeout": False,
            "notify": ["email", "slack"],
        }
    ],
}


def write_temp_config(data: dict) -> str:
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    yaml.dump(data, tmp)
    tmp.close()
    return tmp.name


def test_load_minimal_config():
    path = write_temp_config(MINIMAL_CONFIG)
    try:
        config = load_config(path)
        assert isinstance(config, AppConfig)
        assert len(config.jobs) == 1
        assert config.jobs[0].name == "test_job"
        assert config.jobs[0].timeout == 300
        assert config.log_level == "INFO"
    finally:
        os.unlink(path)


def test_load_full_config():
    path = write_temp_config(FULL_CONFIG)
    try:
        config = load_config(path)
        assert config.log_level == "DEBUG"
        assert config.alerts.email == "admin@example.com"
        assert config.alerts.slack_channel == "#alerts"
        job = config.jobs[0]
        assert job.name == "backup"
        assert job.timeout == 3600
        assert job.alert_on_timeout is False
        assert "email" in job.notify
    finally:
        os.unlink(path)


def test_missing_config_file():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/config.yaml")


def test_empty_config_file():
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    tmp.write("")
    tmp.close()
    try:
        with pytest.raises(ValueError, match="empty or invalid"):
            load_config(tmp.name)
    finally:
        os.unlink(tmp.name)
