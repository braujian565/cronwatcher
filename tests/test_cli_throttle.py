"""Tests for cronwatcher.cli_throttle."""

import argparse
import time
from pathlib import Path

import pytest

from cronwatcher.throttle import Throttler
from cronwatcher.cli_throttle import (
    cmd_throttle_list,
    cmd_throttle_reset,
    register_throttle_subcommand,
)


def _args(tmp_path: Path, **kwargs) -> argparse.Namespace:
    defaults = {
        "state": str(tmp_path / "throttle.json"),
        "cooldown": 3600,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


@pytest.fixture
def populated(tmp_path: Path):
    t = Throttler(state_path=tmp_path / "throttle.json", cooldown_seconds=3600)
    t.record_alert("job_a", now=time.time())
    t.record_alert("job_b", now=time.time())
    return tmp_path


# ---------------------------------------------------------------------------
# cmd_throttle_list
# ---------------------------------------------------------------------------

def test_list_empty(tmp_path: Path, capsys):
    cmd_throttle_list(_args(tmp_path))
    out = capsys.readouterr().out
    assert "No throttle entries" in out


def test_list_shows_jobs(populated: Path, capsys):
    cmd_throttle_list(_args(populated))
    out = capsys.readouterr().out
    assert "job_a" in out
    assert "job_b" in out


def test_list_shows_header(populated: Path, capsys):
    cmd_throttle_list(_args(populated))
    out = capsys.readouterr().out
    assert "JOB" in out
    assert "LAST_ALERTED_AT" in out


# ---------------------------------------------------------------------------
# cmd_throttle_reset
# ---------------------------------------------------------------------------

def test_reset_specific_job(populated: Path, capsys):
    cmd_throttle_reset(_args(populated, job="job_a"))
    out = capsys.readouterr().out
    assert "job_a" in out
    t = Throttler(state_path=populated / "throttle.json")
    assert t.get_entry("job_a") is None
    assert t.get_entry("job_b") is not None


def test_reset_all_jobs(populated: Path, capsys):
    cmd_throttle_reset(_args(populated, job="--all"))
    out = capsys.readouterr().out
    assert "2 job" in out
    t = Throttler(state_path=populated / "throttle.json")
    assert len(t._entries) == 0


# ---------------------------------------------------------------------------
# register_throttle_subcommand
# ---------------------------------------------------------------------------

def test_register_adds_throttle_subcommand():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="cmd")
    register_throttle_subcommand(subs)
    args = parser.parse_args(["throttle", "list"])
    assert args.cmd == "throttle"
