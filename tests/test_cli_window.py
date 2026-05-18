"""Tests for cronwatcher.cli_window."""
from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.cli_window import (
    cmd_window_check,
    cmd_window_list,
    register_window_subcommand,
)


def _args(**kwargs) -> argparse.Namespace:
    defaults = {"config": "cronwatcher.yaml"}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# cmd_window_list
# ---------------------------------------------------------------------------

def test_list_missing_config(capsys):
    with patch("cronwatcher.cli_window.AppConfig") as MockCfg:
        MockCfg.load.side_effect = FileNotFoundError
        cmd_window_list(_args())
    out = capsys.readouterr().out
    assert "not found" in out


def test_list_no_jobs(capsys):
    cfg = MagicMock()
    cfg.jobs = []
    with patch("cronwatcher.cli_window.AppConfig") as MockCfg:
        MockCfg.load.return_value = cfg
        cmd_window_list(_args())
    out = capsys.readouterr().out
    assert "No jobs" in out


def test_list_job_without_windows(capsys):
    job = MagicMock()
    job.name = "backup"
    job.windows = []
    cfg = MagicMock()
    cfg.jobs = [job]
    with patch("cronwatcher.cli_window.AppConfig") as MockCfg:
        MockCfg.load.return_value = cfg
        cmd_window_list(_args())
    out = capsys.readouterr().out
    assert "backup" in out
    assert "any time" in out


def test_list_job_with_window(capsys):
    job = MagicMock()
    job.name = "report"
    job.windows = ["08:00-18:00"]
    cfg = MagicMock()
    cfg.jobs = [job]
    with patch("cronwatcher.cli_window.AppConfig") as MockCfg:
        MockCfg.load.return_value = cfg
        cmd_window_list(_args())
    out = capsys.readouterr().out
    assert "report" in out
    assert "08:00-18:00" in out


# ---------------------------------------------------------------------------
# cmd_window_check
# ---------------------------------------------------------------------------

def test_check_missing_config(capsys):
    with patch("cronwatcher.cli_window.AppConfig") as MockCfg:
        MockCfg.load.side_effect = FileNotFoundError
        cmd_window_check(_args(job="backup"))
    assert "not found" in capsys.readouterr().out


def test_check_unknown_job(capsys):
    cfg = MagicMock()
    cfg.jobs = []
    with patch("cronwatcher.cli_window.AppConfig") as MockCfg:
        MockCfg.load.return_value = cfg
        cmd_window_check(_args(job="ghost"))
    assert "Unknown job" in capsys.readouterr().out


def test_check_allowed_job(capsys):
    job = MagicMock()
    job.name = "sync"
    job.windows = []  # no restriction → always allowed
    cfg = MagicMock()
    cfg.jobs = [job]
    with patch("cronwatcher.cli_window.AppConfig") as MockCfg:
        MockCfg.load.return_value = cfg
        cmd_window_check(_args(job="sync"))
    assert "allowed" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# register_window_subcommand
# ---------------------------------------------------------------------------

def test_register_window_subcommand():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    register_window_subcommand(sub)
    args = parser.parse_args(["window", "list"])
    assert args.cmd == "window"
