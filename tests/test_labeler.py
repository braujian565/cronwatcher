"""Tests for cronwatcher.labeler."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwatcher.config import JobConfig
from cronwatcher.labeler import Labeler


@pytest.fixture()
def labeler(tmp_path: Path) -> Labeler:
    return Labeler(path=tmp_path / "labels.json")


def _job(name: str) -> JobConfig:
    return JobConfig(name=name, schedule="* * * * *", command=f"echo {name}")


# ------------------------------------------------------------------
# Basic get / set / remove
# ------------------------------------------------------------------

def test_get_label_none_when_not_set(labeler: Labeler) -> None:
    assert labeler.get_label("backup") is None


def test_set_and_get_label(labeler: Labeler) -> None:
    labeler.set_label("backup", "Daily Backup")
    assert labeler.get_label("backup") == "Daily Backup"


def test_display_name_falls_back_to_job_name(labeler: Labeler) -> None:
    assert labeler.display_name("cleanup") == "cleanup"


def test_display_name_returns_label_when_set(labeler: Labeler) -> None:
    labeler.set_label("cleanup", "Nightly Cleanup")
    assert labeler.display_name("cleanup") == "Nightly Cleanup"


def test_remove_label_returns_true_when_existed(labeler: Labeler) -> None:
    labeler.set_label("sync", "Sync Job")
    assert labeler.remove_label("sync") is True
    assert labeler.get_label("sync") is None


def test_remove_label_returns_false_when_missing(labeler: Labeler) -> None:
    assert labeler.remove_label("ghost") is False


# ------------------------------------------------------------------
# Persistence
# ------------------------------------------------------------------

def test_labels_persisted_to_disk(tmp_path: Path) -> None:
    lb = Labeler(path=tmp_path / "labels.json")
    lb.set_label("report", "Weekly Report")
    lb2 = Labeler(path=tmp_path / "labels.json")
    assert lb2.get_label("report") == "Weekly Report"


def test_corrupt_file_loads_empty(tmp_path: Path) -> None:
    p = tmp_path / "labels.json"
    p.write_text("NOT JSON")
    lb = Labeler(path=p)
    assert lb.all_labels() == {}


def test_missing_file_loads_empty(tmp_path: Path) -> None:
    lb = Labeler(path=tmp_path / "nonexistent.json")
    assert lb.all_labels() == {}


# ------------------------------------------------------------------
# all_labels / filter_by_label
# ------------------------------------------------------------------

def test_all_labels_returns_copy(labeler: Labeler) -> None:
    labeler.set_label("a", "Alpha")
    result = labeler.all_labels()
    result["b"] = "Beta"
    assert "b" not in labeler.all_labels()


def test_filter_by_label_matches_label(labeler: Labeler) -> None:
    labeler.set_label("backup", "Daily Backup")
    jobs = [_job("backup"), _job("sync")]
    found = labeler.filter_by_label(jobs, "Daily Backup")
    assert [j.name for j in found] == ["backup"]


def test_filter_by_label_case_insensitive(labeler: Labeler) -> None:
    labeler.set_label("report", "Weekly Report")
    jobs = [_job("report"), _job("other")]
    found = labeler.filter_by_label(jobs, "weekly report")
    assert [j.name for j in found] == ["report"]


def test_filter_by_label_falls_back_to_job_name(labeler: Labeler) -> None:
    """If no label is set, job name itself is used for matching."""
    jobs = [_job("cleanup"), _job("backup")]
    found = labeler.filter_by_label(jobs, "cleanup")
    assert [j.name for j in found] == ["cleanup"]


def test_filter_by_label_empty_when_no_match(labeler: Labeler) -> None:
    jobs = [_job("a"), _job("b")]
    assert labeler.filter_by_label(jobs, "zzz") == []
