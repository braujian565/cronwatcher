"""Tests for JobStore and JobRecord."""

import os
import time

import pytest

from cronwatcher.job_store import JobRecord, JobStore


@pytest.fixture
def store(tmp_path):
    return JobStore(store_path=str(tmp_path / "state" / "jobs.json"))


def test_get_new_record_defaults(store):
    rec = store.get("backup")
    assert rec.job_name == "backup"
    assert rec.consecutive_failures == 0
    assert rec.total_runs == 0
    assert rec.last_success is None


def test_record_success(store):
    before = time.time()
    rec = store.record_success("backup")
    assert rec.last_exit_code == 0
    assert rec.consecutive_failures == 0
    assert rec.total_runs == 1
    assert rec.last_success >= before


def test_record_failure(store):
    rec = store.record_failure("backup", exit_code=1)
    assert rec.last_exit_code == 1
    assert rec.consecutive_failures == 1
    assert rec.total_runs == 1


def test_consecutive_failures_accumulate(store):
    store.record_failure("backup", 1)
    store.record_failure("backup", 1)
    rec = store.record_failure("backup", 2)
    assert rec.consecutive_failures == 3


def test_success_resets_consecutive_failures(store):
    store.record_failure("backup", 1)
    store.record_failure("backup", 1)
    rec = store.record_success("backup")
    assert rec.consecutive_failures == 0
    assert rec.total_runs == 3


def test_persistence(tmp_path):
    path = str(tmp_path / "state" / "jobs.json")
    s1 = JobStore(store_path=path)
    s1.record_failure("myjob", 127)

    s2 = JobStore(store_path=path)
    rec = s2.get("myjob")
    assert rec.consecutive_failures == 1
    assert rec.last_exit_code == 127


def test_all_records(store):
    store.record_success("job_a")
    store.record_failure("job_b", 1)
    names = {r.job_name for r in store.all_records()}
    assert names == {"job_a", "job_b"}
