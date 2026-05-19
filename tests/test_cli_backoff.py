"""Tests for cronwatcher.cli_backoff."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.cli_backoff import cmd_backoff, register_backoff_subcommand


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _args(config: str = "cronwatcher/config.example.yaml", job: str | None = None) -> argparse.Namespace:
    ns = argparse.Namespace()
    ns.config = config
    ns.job = job
    return ns


def _fake_app_config(job_names=("backup", "cleanup")):
    jobs = []
    for name in job_names:
        j = MagicMock()
        j.name = name
        j.backoff = None
        jobs.append(j)
    cfg = MagicMock()
    cfg.jobs = jobs
    cfg.defaults = None
    return cfg


# ---------------------------------------------------------------------------
# cmd_backoff
# ---------------------------------------------------------------------------

def test_cmd_backoff_missing_config_exits(capsys):
    with patch("cronwatcher.cli_backoff.load_config", side_effect=FileNotFoundError("not found")):
        with pytest.raises(SystemExit) as exc_info:
            cmd_backoff(_args(config="/no/such/file.yaml"))
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "error" in captured.err


def test_cmd_backoff_unknown_job_exits(capsys):
    with patch("cronwatcher.cli_backoff.load_config", return_value=_fake_app_config(["backup"])):
        with pytest.raises(SystemExit) as exc_info:
            cmd_backoff(_args(job="ghost"))
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "ghost" in captured.err


def test_cmd_backoff_all_jobs_printed(capsys):
    with patch("cronwatcher.cli_backoff.load_config", return_value=_fake_app_config(["backup", "cleanup"])):
        cmd_backoff(_args())
    captured = capsys.readouterr()
    assert "backup" in captured.out
    assert "cleanup" in captured.out


def test_cmd_backoff_single_job_filter(capsys):
    with patch("cronwatcher.cli_backoff.load_config", return_value=_fake_app_config(["backup", "cleanup"])):
        cmd_backoff(_args(job="backup"))
    captured = capsys.readouterr()
    assert "backup" in captured.out
    assert "cleanup" not in captured.out


def test_cmd_backoff_output_contains_header(capsys):
    with patch("cronwatcher.cli_backoff.load_config", return_value=_fake_app_config(["myjob"])):
        cmd_backoff(_args())
    captured = capsys.readouterr()
    assert "JOB" in captured.out
    assert "BASE" in captured.out
    assert "MULT" in captured.out


# ---------------------------------------------------------------------------
# register_backoff_subcommand
# ---------------------------------------------------------------------------

def test_register_adds_backoff_subcommand():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_backoff_subcommand(sub)
    ns = parser.parse_args(["backoff"])
    assert hasattr(ns, "func")


def test_register_backoff_job_flag():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_backoff_subcommand(sub)
    ns = parser.parse_args(["backoff", "--job", "myjob"])
    assert ns.job == "myjob"
