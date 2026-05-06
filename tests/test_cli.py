"""Tests for the cronwatcher CLI module."""

import pytest
from unittest.mock import MagicMock, patch

from cronwatcher.cli import build_parser, cmd_list, cmd_check, main


MINIMAL_CONFIG = """
jobs:
  - name: test-job
    schedule: "* * * * *"
    command: echo hello
"""


@pytest.fixture
def config_file(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(MINIMAL_CONFIG)
    return str(p)


def test_build_parser_defaults():
    parser = build_parser()
    args = parser.parse_args([])
    assert args.config == "cronwatcher/config.example.yaml"
    assert args.verbose is False
    assert args.command is None


def test_build_parser_verbose_flag():
    parser = build_parser()
    args = parser.parse_args(["-v", "run"])
    assert args.verbose is True
    assert args.command == "run"


def test_build_parser_config_short_flag():
    parser = build_parser()
    args = parser.parse_args(["-c", "my.yaml", "check"])
    assert args.config == "my.yaml"
    assert args.command == "check"


def test_cmd_list_output(config_file, capsys):
    cmd_list(config_file)
    captured = capsys.readouterr()
    assert "test-job" in captured.out
    assert "echo hello" in captured.out


def test_cmd_check_no_due_jobs(config_file):
    """cmd_check should not raise even if no jobs are due."""
    with patch("cronwatcher.cli.get_due_jobs", return_value=[]):
        with patch("cronwatcher.cli.JobStore"):
            with patch("cronwatcher.cli.Watcher"):
                cmd_check(config_file)  # should not raise


def test_cmd_check_runs_due_jobs(config_file):
    mock_job = MagicMock()
    mock_watcher = MagicMock()

    with patch("cronwatcher.cli.get_due_jobs", return_value=[mock_job]):
        with patch("cronwatcher.cli.JobStore"):
            with patch("cronwatcher.cli.Watcher", return_value=mock_watcher):
                cmd_check(config_file)
                mock_watcher.run_job.assert_called_once_with(mock_job)


def test_main_list_command(config_file, capsys):
    result = main(["-c", config_file, "list"])
    assert result == 0
    captured = capsys.readouterr()
    assert "test-job" in captured.out


def test_main_missing_config():
    with pytest.raises(SystemExit) as exc_info:
        main(["-c", "/nonexistent/config.yaml", "list"])
    assert exc_info.value.code == 2


def test_main_check_command(config_file):
    with patch("cronwatcher.cli.get_due_jobs", return_value=[]):
        with patch("cronwatcher.cli.JobStore"):
            with patch("cronwatcher.cli.Watcher"):
                result = main(["-c", config_file, "check"])
    assert result == 0
