"""Tests for cronwatcher.cli_forecast."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.cli_forecast import cmd_forecast, register_forecast_subcommand
from cronwatcher.forecast import ForecastEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _args(**kwargs) -> argparse.Namespace:
    defaults = {"config": "cronwatcher/config.example.yaml", "horizon": 24, "tag": None}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _fake_entry(job_name: str, next_run: datetime, tags: list[str] | None = None):
    job = SimpleNamespace(name=job_name, tags=tags or [])
    return ForecastEntry(job=job, next_run=next_run)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_cmd_forecast_missing_config_exits(tmp_path):
    args = _args(config=str(tmp_path / "no_such.yaml"))
    with pytest.raises(SystemExit) as exc_info:
        cmd_forecast(args)
    assert exc_info.value.code == 1


def test_cmd_forecast_prints_table(capsys):
    now = datetime(2024, 6, 1, 10, 0, 0)
    entry = _fake_entry("backup", datetime(2024, 6, 1, 11, 0, 0))

    with patch("cronwatcher.cli_forecast.AppConfig.load") as mock_load, \
         patch("cronwatcher.cli_forecast.compute_forecast", return_value=[entry]), \
         patch("cronwatcher.cli_forecast.format_forecast_table", return_value="TABLE") as mock_fmt:
        mock_load.return_value = MagicMock()
        cmd_forecast(_args())

    captured = capsys.readouterr()
    assert "TABLE" in captured.out


def test_cmd_forecast_empty_forecast_prints_message(capsys):
    with patch("cronwatcher.cli_forecast.AppConfig.load") as mock_load, \
         patch("cronwatcher.cli_forecast.compute_forecast", return_value=[]):
        mock_load.return_value = MagicMock()
        cmd_forecast(_args(horizon=6))

    captured = capsys.readouterr()
    assert "6 hour" in captured.out


def test_cmd_forecast_tag_filter_matches(capsys):
    entry = _fake_entry("db-backup", datetime(2024, 6, 1, 12, 0), tags=["db"])

    with patch("cronwatcher.cli_forecast.AppConfig.load") as mock_load, \
         patch("cronwatcher.cli_forecast.compute_forecast", return_value=[entry]), \
         patch("cronwatcher.cli_forecast.format_forecast_table", return_value="FILTERED"):
        mock_load.return_value = MagicMock()
        cmd_forecast(_args(tag="db"))

    assert "FILTERED" in capsys.readouterr().out


def test_cmd_forecast_tag_filter_no_match_prints_message(capsys):
    entry = _fake_entry("db-backup", datetime(2024, 6, 1, 12, 0), tags=["db"])

    with patch("cronwatcher.cli_forecast.AppConfig.load") as mock_load, \
         patch("cronwatcher.cli_forecast.compute_forecast", return_value=[entry]):
        mock_load.return_value = MagicMock()
        cmd_forecast(_args(tag="nonexistent"))

    assert "nonexistent" in capsys.readouterr().out


def test_register_forecast_subcommand():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    register_forecast_subcommand(subparsers)

    parsed = parser.parse_args(["forecast", "--horizon", "48", "--tag", "web"])
    assert parsed.horizon == 48
    assert parsed.tag == "web"
    assert parsed.func is cmd_forecast
