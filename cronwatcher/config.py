"""Configuration dataclasses and YAML loader for cronwatcher."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

import yaml


@dataclass
class JobConfig:
    name: str
    command: str
    schedule: str
    timeout: Optional[int] = None
    alert_on_failure: bool = True
    retry_attempts: int = 0
    retry_delay: float = 0.0   # seconds between retries


@dataclass
class AlertConfig:
    email_to: Optional[str] = None
    email_from: Optional[str] = None
    smtp_host: str = "localhost"
    smtp_port: int = 25
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None

    def __post_init__(self) -> None:
        if self.smtp_port and not isinstance(self.smtp_port, int):
            self.smtp_port = int(self.smtp_port)


@dataclass
class AppConfig:
    jobs: List[JobConfig] = field(default_factory=list)
    alert: AlertConfig = field(default_factory=AlertConfig)
    store_path: str = "/var/lib/cronwatcher/state.json"
    log_level: str = "INFO"
    check_interval: int = 60   # seconds
    digest_schedule: Optional[str] = None


def _parse_job(raw: dict) -> JobConfig:
    return JobConfig(
        name=raw["name"],
        command=raw["command"],
        schedule=raw["schedule"],
        timeout=raw.get("timeout"),
        alert_on_failure=raw.get("alert_on_failure", True),
        retry_attempts=int(raw.get("retry_attempts", 0)),
        retry_delay=float(raw.get("retry_delay", 0.0)),
    )


def load_config(path: str) -> AppConfig:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path) as fh:
        raw = yaml.safe_load(fh)

    if not raw:
        return AppConfig()

    alert_raw = raw.get("alert", {})
    alert = AlertConfig(
        email_to=alert_raw.get("email_to"),
        email_from=alert_raw.get("email_from"),
        smtp_host=alert_raw.get("smtp_host", "localhost"),
        smtp_port=alert_raw.get("smtp_port", 25),
        smtp_user=alert_raw.get("smtp_user"),
        smtp_password=alert_raw.get("smtp_password"),
    )

    jobs = [_parse_job(j) for j in raw.get("jobs", [])]

    return AppConfig(
        jobs=jobs,
        alert=alert,
        store_path=raw.get("store_path", "/var/lib/cronwatcher/state.json"),
        log_level=raw.get("log_level", "INFO"),
        check_interval=int(raw.get("check_interval", 60)),
        digest_schedule=raw.get("digest_schedule"),
    )
