"""Tests for cronwatcher.cli_labeler."""
from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from cronwatcher.cli_labeler import (
    cmd_label_get,
    cmd_label_list,
    cmd_label_rm,
    cmd_label_set,
    register_labeler_subcommand,
)
from cronwatcher.labeler import Labeler


def _args(tmp_path: Path, **kwargs) -> argparse.Namespace:  # type: ignore[type-arg]
    ns = argparse.Namespace(store_dir=str(tmp_path), **kwargs)
    return ns


# ------------------------------------------------------------------
# cmd_label_set
# ------------------------------------------------------------------

def test_cmd_label_set_prints_confirmation(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    args = _args(tmp_path, job="backup", label="Daily Backup")
    cmd_label_set(args)
    out = capsys.readouterr().out
    assert "backup" in out
    assert "Daily Backup" in out


def test_cmd_label_set_persists(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    args = _args(tmp_path, job="sync", label="Sync Job")
    cmd_label_set(args)
    lb = Labeler(path=tmp_path / "cronwatcher_labels.json")
    assert lb.get_label("sync") == "Sync Job"


# ------------------------------------------------------------------
# cmd_label_get
# ------------------------------------------------------------------

def test_cmd_label_get_existing(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    lb = Labeler(path=tmp_path / "cronwatcher_labels.json")
    lb.set_label("report", "Weekly Report")
    args = _args(tmp_path, job="report")
    cmd_label_get(args)
    out = capsys.readouterr().out
    assert "Weekly Report" in out


def test_cmd_label_get_missing(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    args = _args(tmp_path, job="ghost")
    cmd_label_get(args)
    out = capsys.readouterr().out
    assert "No label" in out


# ------------------------------------------------------------------
# cmd_label_rm
# ------------------------------------------------------------------

def test_cmd_label_rm_existing(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    lb = Labeler(path=tmp_path / "cronwatcher_labels.json")
    lb.set_label("cleanup", "Cleanup")
    args = _args(tmp_path, job="cleanup")
    cmd_label_rm(args)
    out = capsys.readouterr().out
    assert "removed" in out.lower()
    assert lb.get_label("cleanup") is None


def test_cmd_label_rm_missing(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    args = _args(tmp_path, job="nobody")
    cmd_label_rm(args)
    out = capsys.readouterr().out
    assert "No label" in out


# ------------------------------------------------------------------
# cmd_label_list
# ------------------------------------------------------------------

def test_cmd_label_list_empty(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    args = _args(tmp_path)
    cmd_label_list(args)
    out = capsys.readouterr().out
    assert "No labels" in out


def test_cmd_label_list_shows_entries(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    lb = Labeler(path=tmp_path / "cronwatcher_labels.json")
    lb.set_label("backup", "Daily Backup")
    lb.set_label("sync", "Sync Job")
    args = _args(tmp_path)
    cmd_label_list(args)
    out = capsys.readouterr().out
    assert "backup" in out
    assert "Daily Backup" in out
    assert "sync" in out


# ------------------------------------------------------------------
# register_labeler_subcommand
# ------------------------------------------------------------------

def test_register_labeler_subcommand() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    register_labeler_subcommand(sub)
    args = parser.parse_args(["label", "list"])
    assert args.label_action == "list"
