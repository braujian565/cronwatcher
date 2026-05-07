"""Tests for cronwatcher.dependency."""
from __future__ import annotations

import pytest

from cronwatcher.config import JobConfig
from cronwatcher.dependency import (
    DependencyResult,
    check_dependencies,
    filter_runnable_jobs,
)
from cronwatcher.job_store import JobStore


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_job(name: str, depends_on=None, schedule: str = "* * * * *") -> JobConfig:
    job = JobConfig(name=name, command=f"echo {name}", schedule=schedule)
    job.depends_on = depends_on or []
    return job


@pytest.fixture()
def store(tmp_path):
    return JobStore(str(tmp_path / "jobs.json"))


# ---------------------------------------------------------------------------
# DependencyResult
# ---------------------------------------------------------------------------

def test_result_ok_when_no_blocked():
    r = DependencyResult(job_name="j")
    assert r.ok is True
    assert "satisfied" in str(r)


def test_result_not_ok_when_blocked():
    r = DependencyResult(job_name="j", blocked_by=["dep1"])
    assert r.ok is False
    assert "dep1" in str(r)


# ---------------------------------------------------------------------------
# check_dependencies
# ---------------------------------------------------------------------------

def test_no_depends_always_ok(store):
    job = _make_job("standalone")
    result = check_dependencies(job, store)
    assert result.ok


def test_blocked_when_dep_never_run(store):
    job = _make_job("child", depends_on=["parent"])
    result = check_dependencies(job, store)
    assert not result.ok
    assert "parent" in result.blocked_by


def test_blocked_when_dep_last_run_failed(store):
    store.get("parent")  # creates default record
    rec = store.get("parent")
    rec.last_exit_code = 1
    store._data["parent"] = rec
    store._save()

    job = _make_job("child", depends_on=["parent"])
    result = check_dependencies(job, store)
    assert not result.ok


def test_ok_when_dep_last_run_succeeded(store):
    rec = store.get("parent")
    rec.last_exit_code = 0
    store._data["parent"] = rec
    store._save()

    job = _make_job("child", depends_on=["parent"])
    result = check_dependencies(job, store)
    assert result.ok


def test_multiple_deps_one_failing(store):
    for name, code in [("dep_a", 0), ("dep_b", 1)]:
        rec = store.get(name)
        rec.last_exit_code = code
        store._data[name] = rec
    store._save()

    job = _make_job("child", depends_on=["dep_a", "dep_b"])
    result = check_dependencies(job, store)
    assert not result.ok
    assert "dep_b" in result.blocked_by
    assert "dep_a" not in result.blocked_by


# ---------------------------------------------------------------------------
# filter_runnable_jobs
# ---------------------------------------------------------------------------

def test_filter_removes_blocked_jobs(store):
    rec = store.get("parent")
    rec.last_exit_code = 0
    store._data["parent"] = rec
    store._save()

    parent = _make_job("parent")
    child_ok = _make_job("child_ok", depends_on=["parent"])
    child_bad = _make_job("child_bad", depends_on=["missing_dep"])

    runnable = filter_runnable_jobs([parent, child_ok, child_bad], store)
    names = [j.name for j in runnable]
    assert "parent" in names
    assert "child_ok" in names
    assert "child_bad" not in names
