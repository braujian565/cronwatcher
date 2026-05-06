"""Tests for cronwatcher.metrics."""
import json
import pytest
from pathlib import Path

from cronwatcher.metrics import JobMetrics, MetricsStore


@pytest.fixture
def store(tmp_path) -> MetricsStore:
    return MetricsStore(path=str(tmp_path / "metrics.json"))


# ---------------------------------------------------------------------------
# JobMetrics unit tests
# ---------------------------------------------------------------------------

def test_failure_rate_no_runs():
    m = JobMetrics(job_name="backup")
    assert m.failure_rate == 0.0


def test_failure_rate_all_failures():
    m = JobMetrics(job_name="backup", total_runs=4, failed_runs=4)
    assert m.failure_rate == 1.0


def test_failure_rate_partial():
    m = JobMetrics(job_name="backup", total_runs=10, failed_runs=3)
    assert pytest.approx(m.failure_rate) == 0.3


def test_avg_duration_none_when_no_runs():
    m = JobMetrics(job_name="backup")
    assert m.avg_duration_seconds is None


def test_avg_duration_calculated():
    m = JobMetrics(job_name="backup", total_runs=2, total_duration_seconds=10.0)
    assert m.avg_duration_seconds == 5.0


def test_to_dict_and_from_dict_roundtrip():
    m = JobMetrics(job_name="nightly", total_runs=3, successful_runs=2,
                   failed_runs=1, total_duration_seconds=9.0,
                   last_duration_seconds=3.0, last_run_at="2024-01-01T00:00:00+00:00")
    restored = JobMetrics.from_dict(m.to_dict())
    assert restored == m


# ---------------------------------------------------------------------------
# MetricsStore tests
# ---------------------------------------------------------------------------

def test_get_new_job_defaults(store):
    m = store.get("myjob")
    assert m.job_name == "myjob"
    assert m.total_runs == 0
    assert m.failure_rate == 0.0


def test_record_success(store):
    m = store.record("myjob", success=True, duration_seconds=1.5)
    assert m.total_runs == 1
    assert m.successful_runs == 1
    assert m.failed_runs == 0
    assert m.last_duration_seconds == 1.5
    assert m.last_run_at is not None


def test_record_failure(store):
    m = store.record("myjob", success=False, duration_seconds=0.3)
    assert m.failed_runs == 1
    assert m.successful_runs == 0


def test_multiple_records_accumulate(store):
    store.record("j", success=True, duration_seconds=2.0)
    store.record("j", success=False, duration_seconds=4.0)
    m = store.get("j")
    assert m.total_runs == 2
    assert m.total_duration_seconds == 6.0
    assert pytest.approx(m.avg_duration_seconds) == 3.0


def test_persistence(tmp_path):
    path = str(tmp_path / "metrics.json")
    s1 = MetricsStore(path=path)
    s1.record("job1", success=True, duration_seconds=5.0)

    s2 = MetricsStore(path=path)
    m = s2.get("job1")
    assert m.total_runs == 1
    assert m.successful_runs == 1


def test_all_metrics_returns_all(store):
    store.record("a", success=True, duration_seconds=1.0)
    store.record("b", success=False, duration_seconds=2.0)
    names = {m.job_name for m in store.all_metrics()}
    assert names == {"a", "b"}


def test_corrupted_file_resets_gracefully(tmp_path):
    path = tmp_path / "metrics.json"
    path.write_text("NOT VALID JSON")
    store = MetricsStore(path=str(path))
    m = store.get("x")
    assert m.total_runs == 0
