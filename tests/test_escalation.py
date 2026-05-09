"""Tests for cronwatcher.escalation."""
import pytest
from cronwatcher.escalation import (
    EscalationLevel,
    parse_escalation_levels,
    active_escalation,
    build_escalation_subject,
    escalation_channels,
)
from cronwatcher.job_store import JobRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _record(consecutive_failures: int) -> JobRecord:
    r = JobRecord(job_name="backup")
    r.consecutive_failures = consecutive_failures
    return r


LEVELS = [
    EscalationLevel(after_failures=3, channels=["slack"], message_prefix="[WARN]"),
    EscalationLevel(after_failures=6, channels=["pagerduty"], message_prefix="[CRITICAL]"),
]


# ---------------------------------------------------------------------------
# EscalationLevel roundtrip
# ---------------------------------------------------------------------------

def test_escalation_level_roundtrip():
    lv = EscalationLevel(after_failures=5, channels=["email", "slack"], message_prefix="[ESC]")
    assert EscalationLevel.from_dict(lv.to_dict()) == lv


def test_escalation_level_defaults():
    lv = EscalationLevel.from_dict({"after_failures": 2})
    assert lv.channels == []
    assert lv.message_prefix == "[ESCALATED]"


# ---------------------------------------------------------------------------
# parse_escalation_levels
# ---------------------------------------------------------------------------

def test_parse_escalation_levels_sorted():
    raw = [
        {"after_failures": 6, "channels": ["pd"]},
        {"after_failures": 2, "channels": ["slack"]},
    ]
    levels = parse_escalation_levels(raw)
    assert [lv.after_failures for lv in levels] == [2, 6]


# ---------------------------------------------------------------------------
# active_escalation
# ---------------------------------------------------------------------------

def test_no_escalation_below_threshold():
    assert active_escalation(_record(0), LEVELS) is None
    assert active_escalation(_record(2), LEVELS) is None


def test_first_level_triggered():
    result = active_escalation(_record(3), LEVELS)
    assert result is not None
    assert result.after_failures == 3


def test_second_level_triggered():
    result = active_escalation(_record(6), LEVELS)
    assert result is not None
    assert result.after_failures == 6


def test_highest_level_wins_when_exceeded():
    result = active_escalation(_record(10), LEVELS)
    assert result is not None
    assert result.after_failures == 6


def test_no_escalation_empty_levels():
    assert active_escalation(_record(99), []) is None


# ---------------------------------------------------------------------------
# build_escalation_subject
# ---------------------------------------------------------------------------

def test_build_escalation_subject_prepends_prefix():
    lv = EscalationLevel(after_failures=3, message_prefix="[WARN]")
    assert build_escalation_subject("Job failed", lv) == "[WARN] Job failed"


def test_build_escalation_subject_empty_prefix():
    lv = EscalationLevel(after_failures=3, message_prefix="")
    assert build_escalation_subject("Job failed", lv) == "Job failed"


# ---------------------------------------------------------------------------
# escalation_channels
# ---------------------------------------------------------------------------

def test_escalation_channels_no_level():
    assert escalation_channels(["email"], None) == ["email"]


def test_escalation_channels_merges_deduped():
    lv = EscalationLevel(after_failures=3, channels=["slack", "email"])
    result = escalation_channels(["email", "log"], lv)
    assert result == ["email", "log", "slack"]


def test_escalation_channels_preserves_order():
    lv = EscalationLevel(after_failures=3, channels=["pagerduty"])
    result = escalation_channels(["email"], lv)
    assert result == ["email", "pagerduty"]
