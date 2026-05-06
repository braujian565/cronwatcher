"""Tests for cronwatcher.audit."""
import json
import os

import pytest

from cronwatcher.audit import AuditEntry, AuditLog, make_entry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def log_path(tmp_path):
    return str(tmp_path / "audit" / "audit.jsonl")


@pytest.fixture()
def audit_log(log_path):
    return AuditLog(log_path)


# ---------------------------------------------------------------------------
# AuditEntry round-trip
# ---------------------------------------------------------------------------

def test_entry_roundtrip():
    e = AuditEntry(
        job_name="backup",
        timestamp="2024-01-01T00:00:00+00:00",
        exit_code=0,
        duration_seconds=1.5,
        retries=2,
        stderr_snippet="warn",
        tags=["db", "nightly"],
    )
    restored = AuditEntry.from_dict(e.to_dict())
    assert restored.job_name == "backup"
    assert restored.retries == 2
    assert restored.tags == ["db", "nightly"]


def test_entry_from_dict_defaults():
    """Optional fields should default gracefully."""
    d = {
        "job_name": "ping",
        "timestamp": "2024-01-01T00:00:00+00:00",
        "exit_code": 1,
        "duration_seconds": 0.1,
    }
    e = AuditEntry.from_dict(d)
    assert e.retries == 0
    assert e.stderr_snippet is None
    assert e.tags == []


# ---------------------------------------------------------------------------
# AuditLog persistence
# ---------------------------------------------------------------------------

def test_read_all_empty(audit_log):
    assert audit_log.read_all() == []


def test_append_creates_file(audit_log, log_path):
    entry = make_entry("job1", exit_code=0, duration_seconds=0.5)
    audit_log.append(entry)
    assert os.path.exists(log_path)


def test_append_and_read_back(audit_log):
    e1 = make_entry("job_a", 0, 1.0)
    e2 = make_entry("job_b", 1, 2.0, retries=1, stderr="oops")
    audit_log.append(e1)
    audit_log.append(e2)

    entries = audit_log.read_all()
    assert len(entries) == 2
    assert entries[0].job_name == "job_a"
    assert entries[1].exit_code == 1
    assert entries[1].retries == 1


def test_read_for_job_filters(audit_log):
    audit_log.append(make_entry("alpha", 0, 1.0))
    audit_log.append(make_entry("beta", 1, 0.5))
    audit_log.append(make_entry("alpha", 0, 0.8))

    results = audit_log.read_for_job("alpha")
    assert len(results) == 2
    assert all(e.job_name == "alpha" for e in results)


def test_file_is_valid_jsonl(audit_log, log_path):
    audit_log.append(make_entry("j", 0, 0.1, tags=["t1"]))
    with open(log_path) as fh:
        lines = [l.strip() for l in fh if l.strip()]
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["job_name"] == "j"
    assert parsed["tags"] == ["t1"]


# ---------------------------------------------------------------------------
# make_entry helper
# ---------------------------------------------------------------------------

def test_make_entry_truncates_stderr():
    long_stderr = "x" * 500
    e = make_entry("j", 1, 0.1, stderr=long_stderr)
    assert len(e.stderr_snippet) == 200


def test_make_entry_empty_stderr_is_none():
    e = make_entry("j", 0, 0.1, stderr="")
    assert e.stderr_snippet is None
