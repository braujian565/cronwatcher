"""Tests for cronwatcher.circuit_breaker."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from cronwatcher.circuit_breaker import CircuitBreaker, CircuitState


@pytest.fixture
def breaker(tmp_path: Path) -> CircuitBreaker:
    return CircuitBreaker(store_path=tmp_path / "cb.json", threshold=3, reset_after=60)


def test_state_closed_by_default(breaker: CircuitBreaker) -> None:
    state = breaker.get_state("myjob")
    assert not state.is_open
    assert state.failure_count == 0


def test_is_allowed_when_no_state(breaker: CircuitBreaker) -> None:
    assert breaker.is_allowed("myjob") is True


def test_failures_below_threshold_keep_circuit_closed(breaker: CircuitBreaker) -> None:
    breaker.record_failure("myjob")
    breaker.record_failure("myjob")
    state = breaker.get_state("myjob")
    assert not state.is_open
    assert breaker.is_allowed("myjob") is True


def test_threshold_opens_circuit(breaker: CircuitBreaker) -> None:
    for _ in range(3):
        breaker.record_failure("myjob")
    state = breaker.get_state("myjob")
    assert state.is_open
    assert not state.is_half_open
    assert breaker.is_allowed("myjob") is False


def test_success_closes_circuit(breaker: CircuitBreaker) -> None:
    for _ in range(3):
        breaker.record_failure("myjob")
    breaker.record_success("myjob")
    state = breaker.get_state("myjob")
    assert not state.is_open
    assert state.failure_count == 0
    assert breaker.is_allowed("myjob") is True


def test_half_open_after_reset_after(breaker: CircuitBreaker) -> None:
    for _ in range(3):
        breaker.record_failure("myjob")
    state = breaker.get_state("myjob")
    # Backdate opened_at so reset_after has elapsed
    state.opened_at = time.time() - 120
    assert state.is_half_open
    assert breaker.is_allowed("myjob") is True


def test_state_persisted_across_instances(tmp_path: Path) -> None:
    store = tmp_path / "cb.json"
    b1 = CircuitBreaker(store_path=store, threshold=2)
    b1.record_failure("job-a")
    b1.record_failure("job-a")

    b2 = CircuitBreaker(store_path=store, threshold=2)
    state = b2.get_state("job-a")
    assert state.is_open
    assert state.failure_count == 2


def test_reset_removes_state(breaker: CircuitBreaker) -> None:
    for _ in range(3):
        breaker.record_failure("myjob")
    breaker.reset("myjob")
    assert "myjob" not in breaker._states
    assert breaker.is_allowed("myjob") is True


def test_state_roundtrip() -> None:
    original = CircuitState(job_name="x", failure_count=5, opened_at=1234567.0, reset_after=120)
    restored = CircuitState.from_dict(original.to_dict())
    assert restored.job_name == original.job_name
    assert restored.failure_count == original.failure_count
    assert restored.opened_at == original.opened_at
    assert restored.reset_after == original.reset_after


def test_state_from_dict_defaults() -> None:
    state = CircuitState.from_dict({"job_name": "y"})
    assert state.failure_count == 0
    assert state.opened_at is None
    assert state.reset_after == 300
