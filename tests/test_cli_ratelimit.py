"""Tests for cronwatcher.cli_ratelimit."""
import argparse
import time
import pytest
from pathlib import Path
from unittest.mock import patch

from cronwatcher.cli_ratelimit import (
    cmd_ratelimit_list,
    cmd_ratelimit_reset,
    register_ratelimit_subcommand,
    _dispatch,
)
from cronwatcher.ratelimit import RateLimiter


def _args(tmp_path: Path, **kwargs) -> argparse.Namespace:
    store = str(tmp_path / "rl.json")
    defaults = {"ratelimit_store": store, "ratelimit_cmd": "list"}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_list_empty(tmp_path, capsys):
    cmd_ratelimit_list(_args(tmp_path))
    out = capsys.readouterr().out
    assert "No rate limit entries" in out


def test_list_shows_jobs(tmp_path, capsys):
    args = _args(tmp_path)
    limiter = RateLimiter(Path(args.ratelimit_store), window_seconds=3600.0, max_alerts=5)
    now = time.time()
    for i in range(2):
        limiter.record_alert("backup", now=now - i)
    cmd_ratelimit_list(args)
    out = capsys.readouterr().out
    assert "backup" in out
    assert "2" in out


def test_list_shows_limited_flag(tmp_path, capsys):
    args = _args(tmp_path)
    limiter = RateLimiter(Path(args.ratelimit_store), window_seconds=3600.0, max_alerts=3)
    now = time.time()
    for i in range(3):
        limiter.record_alert("myjob", now=now - i)
    # Re-read with same max_alerts via patching
    with patch("cronwatcher.cli_ratelimit._DEFAULT_MAX", 3):
        cmd_ratelimit_list(args)
    out = capsys.readouterr().out
    assert "YES" in out


def test_reset_clears_entry(tmp_path, capsys):
    args = _args(tmp_path, ratelimit_cmd="reset", job="backup")
    limiter = RateLimiter(Path(args.ratelimit_store), window_seconds=3600.0, max_alerts=3)
    now = time.time()
    for i in range(3):
        limiter.record_alert("backup", now=now - i)
    cmd_ratelimit_reset(args)
    out = capsys.readouterr().out
    assert "backup" in out
    limiter2 = RateLimiter(Path(args.ratelimit_store), window_seconds=3600.0, max_alerts=3)
    assert not limiter2.is_limited("backup", now=now)


def test_dispatch_list(tmp_path, capsys):
    args = _args(tmp_path, ratelimit_cmd="list")
    _dispatch(args)
    out = capsys.readouterr().out
    assert "No rate limit entries" in out


def test_dispatch_unknown_exits(tmp_path):
    args = _args(tmp_path, ratelimit_cmd=None)
    with pytest.raises(SystemExit):
        _dispatch(args)


def test_register_adds_subcommand():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_ratelimit_subcommand(sub)
    args = parser.parse_args(["ratelimit", "--help"] if False else ["ratelimit", "list"])
    assert hasattr(args, "func")
