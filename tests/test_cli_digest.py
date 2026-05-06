"""Tests for cronwatcher.cli_digest send-digest sub-command."""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.cli_digest import cmd_send_digest, register_digest_subcommand


@pytest.fixture()
def args(tmp_path):
    a = argparse.Namespace()
    a.config = str(tmp_path / "cronwatcher.yaml")
    a.dry_run = False
    return a


def test_cmd_send_digest_missing_config(args):
    rc = cmd_send_digest(args)
    assert rc == 1


def test_cmd_send_digest_dry_run(tmp_path, args):
    cfg_path = tmp_path / "cronwatcher.yaml"
    cfg_path.write_text(
        "jobs:\n"
        "  - name: test\n"
        "    command: echo hi\n"
        "    schedule: '* * * * *'\n"
        "state_file: " + str(tmp_path / "state.json") + "\n"
    )
    args.config = str(cfg_path)
    args.dry_run = True

    with patch("cronwatcher.cli_digest.send_digest") as mock_send:
        rc = cmd_send_digest(args)

    assert rc == 0
    mock_send.assert_not_called()


def test_cmd_send_digest_sends(tmp_path, args, capsys):
    cfg_path = tmp_path / "cronwatcher.yaml"
    cfg_path.write_text(
        "jobs:\n"
        "  - name: myjob\n"
        "    command: echo hi\n"
        "    schedule: '* * * * *'\n"
        "state_file: " + str(tmp_path / "state.json") + "\n"
    )
    args.config = str(cfg_path)
    args.dry_run = False

    with patch("cronwatcher.cli_digest.send_digest") as mock_send:
        rc = cmd_send_digest(args)

    assert rc == 0
    mock_send.assert_called_once()
    out = capsys.readouterr().out
    assert "Digest sent" in out


def test_register_digest_subcommand():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_digest_subcommand(sub)
    parsed = parser.parse_args(["send-digest"])
    assert hasattr(parsed, "func")
    assert parsed.dry_run is False


def test_register_digest_dry_run_flag():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    register_digest_subcommand(sub)
    parsed = parser.parse_args(["send-digest", "--dry-run"])
    assert parsed.dry_run is True
