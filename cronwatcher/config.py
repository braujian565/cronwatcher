"""Configuration loading for cronwatcher."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class JobConfig:
    name: str
    command: str
    timeout: int = 60
    enabled: bool = True


@dataclass
class AlertConfig:
    email: Optional[str] = None
    on_consecutive_failures: int = 1
    # SMTP settings (can also come from env vars)
    smtp_host: str = "localhost"
    smtp_port: int = 25
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None

    def __post_init__(self) -> None:
        # Allow env-var overrides so secrets stay out of config files
        self.smtp_host = os.environ.get("CRONWATCHER_SMTP_HOST", self.smtp_host)
        self.smtp_port = int(os.environ.get("CRONWATCHER_SMTP_PORT", self.smtp_port))
        self.smtp_user = os.environ.get("CRONWATCHER_SMTP_USER", self.smtp_user)
        self.smtp_password = os.environ.get("CRONWATCHER_SMTP_PASSWORD", self.smtp_password)


@dataclass
class AppConfig:
    jobs: List[JobConfig] = field(default_factory=list)
    alert: AlertConfig = field(default_factory=AlertConfig)
    store_path: str = "/var/lib/cronwatcher/jobs.json"
    log_level: str = "INFO"


def load_config(path: str | Path) -> AppConfig:
    """Load and validate configuration from a YAML file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")

    raw = p.read_text(encoding="utf-8")
    data: dict = yaml.safe_load(raw) or {}

    alert_data = data.get("alert", {})
    alert = AlertConfig(
        email=alert_data.get("email"),
        on_consecutive_failures=alert_data.get("on_consecutive_failures", 1),
        smtp_host=alert_data.get("smtp_host", "localhost"),
        smtp_port=int(alert_data.get("smtp_port", 25)),
        smtp_user=alert_data.get("smtp_user"),
        smtp_password=alert_data.get("smtp_password"),
    )

    jobs = [
        JobConfig(
            name=j["name"],
            command=j["command"],
            timeout=j.get("timeout", 60),
            enabled=j.get("enabled", True),
        )
        for j in data.get("jobs", [])
    ]

    return AppConfig(
        jobs=jobs,
        alert=alert,
        store_path=data.get("store_path", "/var/lib/cronwatcher/jobs.json"),
        log_level=data.get("log_level", "INFO"),
    )
