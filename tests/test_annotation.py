"""Tests for cronwatcher.annotation and cronwatcher.cli_annotation."""
from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from cronwatcher.annotation import Annotation, Annotator
from cronwatcher.cli_annotation import (
    cmd_annotation_add,
    cmd_annotation_clear,
    cmd_annotation_list,
)


@pytest.fixture()
def annotator(tmp_path: Path) -> Annotator:
    return Annotator(tmp_path / "annotations.json")


def test_annotation_roundtrip() -> None:
    a = Annotation(job_name="backup", note="checked manually", author="alice")
    restored = Annotation.from_dict(a.to_dict())
    assert restored.job_name == "backup"
    assert restored.note == "checked manually"
    assert restored.author == "alice"


def test_annotation_defaults() -> None:
    d = {"job_name": "sync", "note": "ok"}
    a = Annotation.from_dict(d)
    assert a.author == "system"
    assert a.created_at  # non-empty


def test_add_and_get(annotator: Annotator) -> None:
    annotator.add(Annotation(job_name="job1", note="first note"))
    annotator.add(Annotation(job_name="job1", note="second note"))
    entries = annotator.get("job1")
    assert len(entries) == 2
    assert entries[0].note == "first note"
    assert entries[1].note == "second note"


def test_get_unknown_job_returns_empty(annotator: Annotator) -> None:
    assert annotator.get("ghost") == []


def test_delete_all_returns_count(annotator: Annotator) -> None:
    annotator.add(Annotation(job_name="job2", note="a"))
    annotator.add(Annotation(job_name="job2", note="b"))
    removed = annotator.delete_all("job2")
    assert removed == 2
    assert annotator.get("job2") == []


def test_delete_all_unknown_returns_zero(annotator: Annotator) -> None:
    assert annotator.delete_all("nope") == 0


def test_all_job_names_sorted(annotator: Annotator) -> None:
    annotator.add(Annotation(job_name="zzz", note="z"))
    annotator.add(Annotation(job_name="aaa", note="a"))
    assert annotator.all_job_names() == ["aaa", "zzz")


def test_persistence(tmp_path: Path) -> None:
    path = tmp_path / "ann.json"
    a1 = Annotator(path)
    a1.add(Annotation(job_name="persist", note="saved"))
    a2 = Annotator(path)
    assert len(a2.get("persist")) == 1


# --- CLI tests ---

def _args(**kwargs) -> argparse.Namespace:
    defaults = {"annotation_store": "/tmp/test_ann_cli.json"}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_cmd_annotation_add_prints_confirmation(tmp_path: Path, capsys) -> None:
    args = _args(
        annotation_store=str(tmp_path / "a.json"),
        job="myjob",
        note="looks good",
        author="bob",
    )
    cmd_annotation_add(args)
    out = capsys.readouterr().out
    assert "myjob" in out


def test_cmd_annotation_list_empty(tmp_path: Path, capsys) -> None:
    args = _args(annotation_store=str(tmp_path / "a.json"), job=None)
    cmd_annotation_list(args)
    out = capsys.readouterr().out
    assert "No annotations" in out


def test_cmd_annotation_clear_prints_count(tmp_path: Path, capsys) -> None:
    store = tmp_path / "a.json"
    ann = Annotator(store)
    ann.add(Annotation(job_name="j", note="x"))
    args = _args(annotation_store=str(store), job="j")
    cmd_annotation_clear(args)
    out = capsys.readouterr().out
    assert "1" in out
