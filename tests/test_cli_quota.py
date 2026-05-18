"""Tests for cronwatcher.cli_quota."""
from __future__ import annotations

import argparse
import pytest

from cronwatcher.quota import QuotaManager
from cronwatcher.cli_quota import (
    cmd_quota_list,
    cmd_quota_set,
    cmd_quota_reset,
    cmd_quota_remove,
    register_quota_subcommand,
)


def _args(tmp_path, **kwargs) -> argparse.Namespace:
    defaults = {"quota_file": str(tmp_path / "quotas.json")}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


@pytest.fixture()
def populated(tmp_path):
    mgr = QuotaManager(store_path=str(tmp_path / "quotas.json"))
    mgr.set_quota("daily_sync", max_runs=3, window_seconds=86400)
    mgr.record_run("daily_sync")
    return tmp_path


def test_list_empty(tmp_path, capsys):
    cmd_quota_list(_args(tmp_path))
    out = capsys.readouterr().out
    assert "No quotas" in out


def test_list_shows_jobs(populated, capsys):
    cmd_quota_list(_args(populated))
    out = capsys.readouterr().out
    assert "daily_sync" in out
    assert "3" in out


def test_list_shows_exceeded_flag(tmp_path, capsys):
    mgr = QuotaManager(store_path=str(tmp_path / "quotas.json"))
    mgr.set_quota("tight", max_runs=1, window_seconds=60)
    mgr.record_run("tight")
    cmd_quota_list(_args(tmp_path))
    out = capsys.readouterr().out
    assert "YES" in out


def test_set_creates_quota(tmp_path, capsys):
    args = _args(tmp_path, job="new_job", max_runs=5, window_seconds=3600)
    cmd_quota_set(args)
    out = capsys.readouterr().out
    assert "new_job" in out
    assert "5" in out
    mgr = QuotaManager(store_path=str(tmp_path / "quotas.json"))
    assert mgr.get_entry("new_job") is not None


def test_reset_clears_counters(populated, capsys):
    args = _args(populated, job="daily_sync")
    cmd_quota_reset(args)
    capsys.readouterr()
    mgr = QuotaManager(store_path=str(populated / "quotas.json"))
    assert mgr.get_entry("daily_sync").count_in_window() == 0


def test_reset_missing_job(tmp_path, capsys):
    args = _args(tmp_path, job="ghost")
    cmd_quota_reset(args)
    out = capsys.readouterr().out
    assert "No quota found" in out


def test_remove_existing(populated, capsys):
    args = _args(populated, job="daily_sync")
    cmd_quota_remove(args)
    out = capsys.readouterr().out
    assert "removed" in out
    mgr = QuotaManager(store_path=str(populated / "quotas.json"))
    assert mgr.get_entry("daily_sync") is None


def test_remove_missing(tmp_path, capsys):
    args = _args(tmp_path, job="ghost")
    cmd_quota_remove(args)
    out = capsys.readouterr().out
    assert "No quota found" in out


def test_register_quota_subcommand():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    register_quota_subcommand(sub)
    args = parser.parse_args(["quota", "list"])
    assert args.quota_cmd == "list"
