"""Escalation policy: send alerts to additional channels after N consecutive failures."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronwatcher.config import JobConfig, AlertConfig
from cronwatcher.job_store import JobRecord


@dataclass
class EscalationLevel:
    """A single escalation tier."""
    after_failures: int          # trigger after this many consecutive failures
    channels: List[str] = field(default_factory=list)  # extra channels to notify
    message_prefix: str = "[ESCALATED]"  # prepended to alert subject

    def to_dict(self) -> dict:
        return {
            "after_failures": self.after_failures,
            "channels": list(self.channels),
            "message_prefix": self.message_prefix,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EscalationLevel":
        return cls(
            after_failures=int(data["after_failures"]),
            channels=list(data.get("channels", [])),
            message_prefix=data.get("message_prefix", "[ESCALATED]"),
        )


def parse_escalation_levels(raw: list) -> List[EscalationLevel]:
    """Parse a list of dicts (from YAML config) into EscalationLevel objects."""
    levels = [EscalationLevel.from_dict(item) for item in raw]
    return sorted(levels, key=lambda lv: lv.after_failures)


def active_escalation(
    record: JobRecord,
    levels: List[EscalationLevel],
) -> Optional[EscalationLevel]:
    """Return the highest escalation level triggered by the record's consecutive failures.

    Returns None when no level is triggered.
    """
    failures = record.consecutive_failures
    triggered: Optional[EscalationLevel] = None
    for level in levels:  # already sorted ascending
        if failures >= level.after_failures:
            triggered = level
    return triggered


def build_escalation_subject(base_subject: str, level: EscalationLevel) -> str:
    """Prepend the escalation prefix to an existing alert subject."""
    prefix = level.message_prefix.strip()
    if not prefix:
        return base_subject
    return f"{prefix} {base_subject}"


def escalation_channels(
    base_channels: List[str],
    level: Optional[EscalationLevel],
) -> List[str]:
    """Merge base channels with escalation-level channels (deduped, order preserved)."""
    if level is None:
        return list(base_channels)
    seen: set = set()
    result: List[str] = []
    for ch in list(base_channels) + list(level.channels):
        if ch not in seen:
            seen.add(ch)
            result.append(ch)
    return result
