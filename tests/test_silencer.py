"""Tests for cronwatcher.silencer."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from cronwatcher.silencer import Silencer, SilenceEntry


UTC = timezone.utc


@pytest.fixture()
def tmp_path_silence(tmp_path):
    return str(tmp_path / "silences.json")


@pytest.fixture()
def silencer(tmp_path_silence):
    return Silencer(path=tmp_path_silence)


def _future(minutes: int = 60) -> datetime:
    return datetime.now(UTC) + timedelta(minutes=minutes)


def _past(minutes: int = 60) -> datetime:
    return datetime.now(UTC) - timedelta(minutes=minutes)


# --- SilenceEntry unit tests ---

def test_silence_entry_active_when_future():
    entry = SilenceEntry(job_name="backup", until=_future())
    assert entry.is_active() is True


def test_silence_entry_inactive_when_past():
    entry = SilenceEntry(job_name="backup", until=_past())
    assert entry.is_active() is False


def test_silence_entry_roundtrip():
    until = _future()
    entry = SilenceEntry(job_name="myjob", until=until, reason="maintenance")
    restored = SilenceEntry.from_dict(entry.to_dict())
    assert restored.job_name == entry.job_name
    assert restored.reason == entry.reason
    assert abs((restored.until - entry.until).total_seconds()) < 1


# --- Silencer tests ---

def test_is_silenced_false_by_default(silencer):
    assert silencer.is_silenced("nightly") is False


def test_silence_makes_job_silenced(silencer):
    silencer.silence("nightly", _future(), reason="deploy")
    assert silencer.is_silenced("nightly") is True


def test_expired_silence_not_active(silencer):
    silencer.silence("nightly", _past())
    assert silencer.is_silenced("nightly") is False


def test_unsilence_removes_entry(silencer):
    silencer.silence("nightly", _future())
    result = silencer.unsilence("nightly")
    assert result is True
    assert silencer.is_silenced("nightly") is False


def test_unsilence_nonexistent_returns_false(silencer):
    assert silencer.unsilence("ghost") is False


def test_active_silences_filters_expired(silencer):
    silencer.silence("job_a", _future())
    silencer.silence("job_b", _past())
    active = silencer.active_silences()
    names = [e.job_name for e in active]
    assert "job_a" in names
    assert "job_b" not in names


def test_silences_persisted_to_disk(tmp_path_silence):
    s1 = Silencer(path=tmp_path_silence)
    s1.silence("backup", _future(), reason="planned")

    s2 = Silencer(path=tmp_path_silence)
    assert s2.is_silenced("backup") is True
    assert s2._silences["backup"].reason == "planned"


def test_file_missing_starts_empty(tmp_path_silence):
    assert not os.path.exists(tmp_path_silence)
    s = Silencer(path=tmp_path_silence)
    assert s.active_silences() == []
