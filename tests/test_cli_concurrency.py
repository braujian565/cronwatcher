"""Tests for cronwatcher.cli_concurrency."""
from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from cronwatcher.cli_concurrency import (
    cmd_concurrency_list,
    cmd_concurrency_remove,
    cmd_concurrency_release,
    cmd_concurrency_set,
    register_concurrency_subcommand,
)
from cronwatcher.concurrency import ConcurrencyManager


def _args(tmp_path: Path, **kwargs) -> argparse.Namespace:  # type: ignore[type-arg]
    base = {"store": str(tmp_path / "concurrency.json")}
    base.update(kwargs)
    return argparse.Namespace(**base)


@pytest.fixture()
def populated(tmp_path: Path) -> argparse.Namespace:
    mgr = ConcurrencyManager(store_path=tmp_path / "concurrency.json")
    mgr.set_limit("batch", 3)
    mgr.acquire("batch", "job_a")
    return _args(tmp_path)


def test_list_empty(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    cmd_concurrency_list(_args(tmp_path))
    out = capsys.readouterr().out
    assert "No concurrency limits" in out


def test_list_shows_limits(populated: argparse.Namespace, capsys: pytest.CaptureFixture) -> None:
    cmd_concurrency_list(populated)
    out = capsys.readouterr().out
    assert "batch" in out
    assert "3" in out


def test_set_creates_limit(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    args = _args(tmp_path, name="etl", max=4)
    cmd_concurrency_set(args)
    out = capsys.readouterr().out
    assert "etl" in out
    assert "4" in out
    mgr = ConcurrencyManager(store_path=tmp_path / "concurrency.json")
    assert mgr.get_limit("etl") is not None


def test_release_frees_slot(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    mgr = ConcurrencyManager(store_path=tmp_path / "concurrency.json")
    mgr.set_limit("batch", 1)
    mgr.acquire("batch", "job_a")

    args = _args(tmp_path, name="batch", job="job_a")
    cmd_concurrency_release(args)
    out = capsys.readouterr().out
    assert "job_a" in out

    mgr2 = ConcurrencyManager(store_path=tmp_path / "concurrency.json")
    lim = mgr2.get_limit("batch")
    assert lim is not None
    assert "job_a" not in lim.running


def test_remove_existing(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    mgr = ConcurrencyManager(store_path=tmp_path / "concurrency.json")
    mgr.set_limit("old", 2)
    args = _args(tmp_path, name="old")
    cmd_concurrency_remove(args)
    out = capsys.readouterr().out
    assert "removed" in out


def test_remove_missing(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    args = _args(tmp_path, name="ghost")
    cmd_concurrency_remove(args)
    out = capsys.readouterr().out
    assert "No limit" in out


def test_register_subcommand() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    register_concurrency_subcommand(sub)
    ns = parser.parse_args(["concurrency", "list"])
    assert ns.cmd == "concurrency"
    assert ns.concurrency_cmd == "list"
