"""Tests for cronwatcher.forecast."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from cronwatcher.forecast import (
    ForecastEntry,
    compute_forecast,
    format_forecast_table,
)


def _make_app_config(*schedules: str):
    jobs = []
    for i, sched in enumerate(schedules):
        j = MagicMock()
        j.name = f"job_{i}"
        j.schedule = sched
        jobs.append(j)
    cfg = MagicMock()
    cfg.jobs = jobs
    return cfg


def _fixed_is_due(job, dt: datetime) -> bool:
    """Stub: job is due if minute == 0 (top of any hour)."""
    return dt.minute == 0


@patch("cronwatcher.forecast.is_job_due", side_effect=_fixed_is_due)
def test_compute_forecast_finds_next_hour(mock_due):
    cfg = _make_app_config("0 * * * *")
    after = datetime(2024, 6, 1, 10, 15)  # 10:15 — next top-of-hour is 11:00
    entries = compute_forecast(cfg, after=after, horizon_minutes=120)
    assert len(entries) == 1
    assert entries[0].job_name == "job_0"
    assert entries[0].next_run == datetime(2024, 6, 1, 11, 0)
    assert entries[0].minutes_away == 45


@patch("cronwatcher.forecast.is_job_due", return_value=False)
def test_compute_forecast_no_match_within_horizon(mock_due):
    cfg = _make_app_config("0 0 31 2 *")  # impossible schedule
    after = datetime(2024, 6, 1, 10, 0)
    entries = compute_forecast(cfg, after=after, horizon_minutes=60)
    assert entries == []


@patch("cronwatcher.forecast.is_job_due", side_effect=_fixed_is_due)
def test_compute_forecast_sorted_by_next_run(mock_due):
    cfg = _make_app_config("0 * * * *", "0 * * * *")
    after = datetime(2024, 6, 1, 10, 30)
    entries = compute_forecast(cfg, after=after, horizon_minutes=120)
    # Both jobs share the same next_run; order is stable but both present
    assert len(entries) == 2
    assert entries[0].next_run <= entries[1].next_run


def test_forecast_entry_str():
    e = ForecastEntry(
        job_name="backup",
        next_run=datetime(2024, 6, 1, 12, 0),
        minutes_away=30,
    )
    s = str(e)
    assert "backup" in s
    assert "2024-06-01 12:00" in s
    assert "30" in s


def test_format_forecast_table_empty():
    result = format_forecast_table([])
    assert "No scheduled" in result


def test_format_forecast_table_with_entries():
    entries = [
        ForecastEntry("alpha", datetime(2024, 6, 1, 11, 0), 60),
        ForecastEntry("beta", datetime(2024, 6, 1, 12, 0), 120),
    ]
    table = format_forecast_table(entries)
    assert "alpha" in table
    assert "beta" in table
    assert "JOB" in table
    assert "NEXT RUN" in table
    assert "IN (min)" in table
