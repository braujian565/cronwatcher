"""Tests for cronwatcher.cli_runlock."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pytest

from cronwatcher.cli_runlock import (
    cmd_runlock_clear,
    cmd_runlock_list,
    register_runlock_subcommand,
)
from cronwatcher.runlock import LockEntry, RunLock


def _args(lock_dir: Path, **kwargs) -> argparse.Namespace:
    ns = argparse.Namespace(lock_dir=str(lock_dir))
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


@pytest.fixture
def lock_dir(tmp_path):
    d = tmp_path / "locks"
    d.mkdir()
    return d


def test_list_empty(lock_dir, capsys):
    cmd_runlock_list(_args(lock_dir))
    out = capsys.readouterr().out
    assert "No active locks" in out


def test_list_shows_active_lock(lock_dir, capsys):
    rl = RunLock(lock_dir)
    rl.acquire("backup")
    cmd_runlock_list(_args(lock_dir))
    out = capsys.readouterr().out
    assert "backup" in out
    assert str(os.getpid()) in out


def test_list_skips_stale_lock(lock_dir, capsys):
    stale = LockEntry(job_name="ghost", pid=999_999_999)
    (lock_dir / "ghost.lock").write_text(json.dumps(stale.to_dict()))
    cmd_runlock_list(_args(lock_dir))
    out = capsys.readouterr().out
    # stale entry has no valid entry returned by current_entry
    assert "ghost" not in out


def test_clear_existing_lock(lock_dir, capsys):
    rl = RunLock(lock_dir)
    rl.acquire("cleanup")
    cmd_runlock_clear(_args(lock_dir, job="cleanup"))
    out = capsys.readouterr().out
    assert "cleared" in out
    assert not rl.is_locked("cleanup")


def test_clear_missing_lock_exits(lock_dir):
    with pytest.raises(SystemExit) as exc_info:
        cmd_runlock_clear(_args(lock_dir, job="nonexistent"))
    assert exc_info.value.code == 1


def test_register_subcommand_list():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    register_runlock_subcommand(sub)
    args = parser.parse_args(["runlock", "list"])
    assert args.runlock_cmd == "list"


def test_register_subcommand_clear():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    register_runlock_subcommand(sub)
    args = parser.parse_args(["runlock", "clear", "myjob"])
    assert args.runlock_cmd == "clear"
    assert args.job == "myjob"


def test_dispatch_list(lock_dir, capsys):
    from cronwatcher.cli_runlock import _dispatch
    ns = _args(lock_dir, runlock_cmd="list")
    _dispatch(ns)
    assert "No active locks" in capsys.readouterr().out


def test_dispatch_clear(lock_dir, capsys):
    from cronwatcher.cli_runlock import _dispatch
    rl = RunLock(lock_dir)
    rl.acquire("myjob")
    ns = _args(lock_dir, runlock_cmd="clear", job="myjob")
    _dispatch(ns)
    assert "cleared" in capsys.readouterr().out
