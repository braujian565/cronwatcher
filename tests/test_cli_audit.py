"""Tests for cronwatcher.cli_audit."""
import argparse
from unittest.mock import patch

import pytest

from cronwatcher.audit import AuditLog, make_entry
from cronwatcher.cli_audit import cmd_audit_list, register_audit_subcommand


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_args(tmp_path, job=None, limit=20):
    log_path = str(tmp_path / "audit.jsonl")
    ns = argparse.Namespace(audit_file=log_path, job=job, limit=limit)
    return ns, AuditLog(log_path)


# ---------------------------------------------------------------------------
# cmd_audit_list
# ---------------------------------------------------------------------------

def test_empty_log_prints_message(tmp_path, capsys):
    args, _ = _make_args(tmp_path)
    rc = cmd_audit_list(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "No audit entries" in out


def test_lists_entries(tmp_path, capsys):
    args, log = _make_args(tmp_path)
    log.append(make_entry("backup", 0, 1.23, tags=["nightly"]))
    log.append(make_entry("cleanup", 1, 0.5, stderr="err"))

    rc = cmd_audit_list(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "backup" in out
    assert "cleanup" in out
    assert "OK" in out
    assert "FAIL(1)" in out


def test_filter_by_job(tmp_path, capsys):
    args, log = _make_args(tmp_path, job="backup")
    log.append(make_entry("backup", 0, 1.0))
    log.append(make_entry("other", 0, 0.5))

    cmd_audit_list(args)
    out = capsys.readouterr().out
    assert "backup" in out
    assert "other" not in out


def test_limit_respected(tmp_path, capsys):
    args, log = _make_args(tmp_path, limit=2)
    for i in range(5):
        log.append(make_entry(f"job{i}", 0, float(i)))

    cmd_audit_list(args)
    out = capsys.readouterr().out
    # 2 entries shown means 2 lines with job names
    lines = [l for l in out.splitlines() if "job" in l]
    assert len(lines) == 2


def test_stderr_snippet_shown(tmp_path, capsys):
    args, log = _make_args(tmp_path)
    log.append(make_entry("job", 1, 0.1, stderr="connection refused"))

    cmd_audit_list(args)
    out = capsys.readouterr().out
    assert "connection refused" in out


def test_tags_shown(tmp_path, capsys):
    args, log = _make_args(tmp_path)
    log.append(make_entry("job", 0, 0.1, tags=["db", "prod"]))

    cmd_audit_list(args)
    out = capsys.readouterr().out
    assert "db" in out
    assert "prod" in out


# ---------------------------------------------------------------------------
# register_audit_subcommand
# ---------------------------------------------------------------------------

def test_register_creates_audit_subcommand():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="cmd")
    register_audit_subcommand(subs)

    parsed = parser.parse_args(
        ["audit", "list", "--limit", "5", "--audit-file", "/tmp/a.jsonl"]
    )
    assert parsed.limit == 5
    assert parsed.audit_file == "/tmp/a.jsonl"


def test_register_default_limit():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="cmd")
    register_audit_subcommand(subs)

    parsed = parser.parse_args(["audit", "list", "--audit-file", "/tmp/a.jsonl"])
    assert parsed.limit == 20
