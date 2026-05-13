"""Tests for cronwatcher.checkpoint and cronwatcher.cli_checkpoint."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
from io import StringIO
from unittest import mock

import pytest

from cronwatcher.checkpoint import CheckpointEntry, Checkpointer
from cronwatcher.cli_checkpoint import (
    cmd_checkpoint_list,
    cmd_checkpoint_show,
    cmd_checkpoint_delete,
    register_checkpoint_subcommand,
)


@pytest.fixture()
def checkpointer(tmp_path):
    return Checkpointer(str(tmp_path / "checkpoints"))


_TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_entry_roundtrip():
    entry = CheckpointEntry(job_name="backup", last_success=_TS)
    restored = CheckpointEntry.from_dict(entry.to_dict())
    assert restored.job_name == "backup"
    assert restored.last_success == _TS


def test_age_seconds():
    entry = CheckpointEntry(job_name="backup", last_success=_TS)
    now = _TS + timedelta(seconds=300)
    assert entry.age_seconds(now=now) == pytest.approx(300.0)


def test_save_and_load(checkpointer):
    checkpointer.save("myjob", _TS)
    entry = checkpointer.load("myjob")
    assert entry is not None
    assert entry.job_name == "myjob"
    assert entry.last_success == _TS


def test_load_missing_returns_none(checkpointer):
    assert checkpointer.load("nonexistent") is None


def test_delete_existing(checkpointer):
    checkpointer.save("myjob", _TS)
    assert checkpointer.delete("myjob") is True
    assert checkpointer.load("myjob") is None


def test_delete_missing_returns_false(checkpointer):
    assert checkpointer.delete("ghost") is False


def test_all_entries_sorted(checkpointer):
    checkpointer.save("zebra", _TS)
    checkpointer.save("alpha", _TS + timedelta(hours=1))
    entries = checkpointer.all_entries()
    assert [e.job_name for e in entries] == ["alpha", "zebra"]


def test_all_entries_empty(checkpointer):
    assert checkpointer.all_entries() == []


def _make_args(tmp_path, **kwargs):
    ns = argparse.Namespace(checkpoint_dir=str(tmp_path / "checkpoints"), **kwargs)
    return ns


def test_cmd_list_empty(tmp_path, capsys):
    cmd_checkpoint_list(_make_args(tmp_path))
    assert "No checkpoints found" in capsys.readouterr().out


def test_cmd_list_shows_entry(tmp_path, capsys):
    cp = Checkpointer(str(tmp_path / "checkpoints"))
    cp.save("backup", _TS)
    cmd_checkpoint_list(_make_args(tmp_path))
    out = capsys.readouterr().out
    assert "backup" in out
    assert "2024-06-01" in out


def test_cmd_show_existing(tmp_path, capsys):
    cp = Checkpointer(str(tmp_path / "checkpoints"))
    cp.save("backup", _TS)
    cmd_checkpoint_show(_make_args(tmp_path, job="backup"))
    out = capsys.readouterr().out
    assert "backup" in out
    assert "Last success" in out


def test_cmd_show_missing(tmp_path, capsys):
    cmd_checkpoint_show(_make_args(tmp_path, job="ghost"))
    assert "No checkpoint found" in capsys.readouterr().out


def test_cmd_delete_existing(tmp_path, capsys):
    cp = Checkpointer(str(tmp_path / "checkpoints"))
    cp.save("backup", _TS)
    cmd_checkpoint_delete(_make_args(tmp_path, job="backup"))
    assert "deleted" in capsys.readouterr().out
    assert cp.load("backup") is None


def test_register_checkpoint_subcommand():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers()
    register_checkpoint_subcommand(subs)
    args = parser.parse_args(["checkpoint", "list"])
    assert args.checkpoint_sub == "list"
