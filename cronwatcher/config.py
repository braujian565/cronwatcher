"""Configuration dataclasses and YAML loader for cronwatcher.

Extended to support an optional ``tags`` list on each JobConfig so that
jobs can be grouped and filtered at runtime.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

log = logging.getLogger(__name__)


@dataclass
class AlertConfig:
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_addr: str = ""
    to_addrs: List[str] = field(default_factory=list)
    use_tls: bool = True


@dataclass
class JobConfig:
    name: str = ""
    command: str = ""
    schedule: str = ""  # cron expression
    timeout: int = 60
    retries: int = 0
    alert_after: int = 1
    tags: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Job must have a name")
        if not self.command:
            raise ValueError(f"Job '{self.name}' must have a command")


@dataclass
class AppConfig:
    jobs: List[JobConfig] = field(default_factory=list)
    alert: Optional[AlertConfig] = None
    store_path: str = "/var/lib/cronwatcher/jobs.json"
    log_level: str = "INFO"
    check_interval: int = 60


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_job(raw: Dict[str, Any]) -> JobConfig:
    return JobConfig(
        name=raw["name"],
        command=raw["command"],
        schedule=raw.get("schedule", ""),
        timeout=int(raw.get("timeout", 60)),
        retries=int(raw.get("retries", 0)),
        alert_after=int(raw.get("alert_after", 1)),
        tags=[str(t) for t in raw.get("tags", [])],
    )


def _parse_alert(raw: Dict[str, Any]) -> AlertConfig:
    return AlertConfig(
        smtp_host=raw.get("smtp_host", ""),
        smtp_port=int(raw.get("smtp_port", 587)),
        smtp_user=raw.get("smtp_user", ""),
        smtp_password=raw.get("smtp_password", ""),
        from_addr=raw.get("from_addr", ""),
        to_addrs=raw.get("to_addrs", []),
        use_tls=bool(raw.get("use_tls", True)),
    )


def load_config(path: str | Path) -> AppConfig:
    """Load and validate an AppConfig from a YAML file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")
    with p.open() as fh:
        data = yaml.safe_load(fh)
    if not data:
        raise ValueError("Config file is empty or invalid YAML")

    jobs = [_parse_job(j) for j in data.get("jobs", [])]
    alert_raw = data.get("alert")
    alert = _parse_alert(alert_raw) if alert_raw else None

    return AppConfig(
        jobs=jobs,
        alert=alert,
        store_path=data.get("store_path", "/var/lib/cronwatcher/jobs.json"),
        log_level=data.get("log_level", "INFO"),
        check_interval=int(data.get("check_interval", 60)),
    )
