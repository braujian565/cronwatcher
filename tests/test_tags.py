"""Tests for cronwatcher.tags — tag-based job filtering."""
from __future__ import annotations

import pytest

from cronwatcher.config import AppConfig, JobConfig
from cronwatcher.tags import (
    TagIndex,
    filter_jobs_by_tags,
    jobs_from_app_config,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def jobs() -> list[JobConfig]:
    return [
        JobConfig(name="backup-db", command="backup.sh", tags=["backup", "database"]),
        JobConfig(name="send-report", command="report.py", tags=["reports", "weekly"]),
        JobConfig(name="cleanup-tmp", command="find /tmp", tags=["maintenance"]),
        JobConfig(name="no-tags", command="echo hi", tags=[]),
    ]


@pytest.fixture()
def index(jobs) -> TagIndex:
    idx = TagIndex()
    idx.build(jobs)
    return idx


# ---------------------------------------------------------------------------
# TagIndex tests
# ---------------------------------------------------------------------------

def test_all_tags_sorted(index):
    assert index.all_tags() == ["backup", "database", "maintenance", "reports", "weekly"]


def test_jobs_for_known_tag(index):
    assert index.jobs_for_tag("backup") == ["backup-db"]


def test_jobs_for_tag_multiple_jobs(index):
    # both backup-db and send-report share no common tag; weekly is exclusive
    assert index.jobs_for_tag("weekly") == ["send-report"]


def test_jobs_for_unknown_tag_returns_empty(index):
    assert index.jobs_for_tag("nonexistent") == []


def test_build_clears_previous_state(jobs):
    idx = TagIndex()
    idx.build(jobs)
    # rebuild with a single job
    idx.build([JobConfig(name="only", command="x", tags=["solo"])])
    assert idx.all_tags() == ["solo"]
    assert idx.jobs_for_tag("backup") == []


# ---------------------------------------------------------------------------
# filter_jobs_by_tags tests
# ---------------------------------------------------------------------------

def test_filter_no_tags_returns_all(jobs):
    assert filter_jobs_by_tags(jobs, None) == jobs
    assert filter_jobs_by_tags(jobs, []) == jobs


def test_filter_single_tag(jobs):
    result = filter_jobs_by_tags(jobs, ["backup"])
    assert len(result) == 1
    assert result[0].name == "backup-db"


def test_filter_multiple_tags_union(jobs):
    result = filter_jobs_by_tags(jobs, ["backup", "maintenance"])
    names = {j.name for j in result}
    assert names == {"backup-db", "cleanup-tmp"}


def test_filter_tag_with_no_match(jobs):
    result = filter_jobs_by_tags(jobs, ["unknown"])
    assert result == []


def test_filter_job_with_no_tags_excluded(jobs):
    result = filter_jobs_by_tags(jobs, ["backup"])
    assert all(j.name != "no-tags" for j in result)


# ---------------------------------------------------------------------------
# jobs_from_app_config tests
# ---------------------------------------------------------------------------

def test_jobs_from_app_config_no_filter(jobs):
    cfg = AppConfig(jobs=jobs)
    assert jobs_from_app_config(cfg) == jobs


def test_jobs_from_app_config_with_tags(jobs):
    cfg = AppConfig(jobs=jobs)
    result = jobs_from_app_config(cfg, tags=["weekly"])
    assert len(result) == 1
    assert result[0].name == "send-report"
