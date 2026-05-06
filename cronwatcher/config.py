"""Configuration loading for cronwatcher."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

import yaml


@dataclass
class JobConfig:
    name: str
    command: str
    schedule: str  # cron expression
    timeout: int = 60
    alert_on_failure: bool = True
    notify_channels: List[str] = field(default_factory=lambda: ["log"])


@dataclass
class AlertConfig:
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    from_address: Optional[str] = None
    to_addresses: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.to_addresses, str):
            self.to_addresses = [self.to_addresses]


@dataclass
class AppConfig:
    jobs: List[JobConfig] = field(default_factory=list)
    alert: AlertConfig = field(default_factory=AlertConfig)
    store_path: str = "/var/lib/cronwatcher/jobs.json"
    check_interval: int = 60
    default_notify_channels: List[str] = field(default_factory=lambda: ["log"])


def load_config(path: str) -> AppConfig:
    """Load and validate configuration from a YAML file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    if not raw:
        return AppConfig()

    alert_raw = raw.get("alert", {})
    alert_cfg = AlertConfig(**{k: v for k, v in alert_raw.items() if k in AlertConfig.__dataclass_fields__})

    default_channels = raw.get("default_notify_channels", ["log"])

    jobs: List[JobConfig] = []
    for j in raw.get("jobs", []):
        jobs.append(
            JobConfig(
                name=j["name"],
                command=j["command"],
                schedule=j["schedule"],
                timeout=j.get("timeout", 60),
                alert_on_failure=j.get("alert_on_failure", True),
                notify_channels=j.get("notify_channels", default_channels),
            )
        )

    return AppConfig(
        jobs=jobs,
        alert=alert_cfg,
        store_path=raw.get("store_path", "/var/lib/cronwatcher/jobs.json"),
        check_interval=raw.get("check_interval", 60),
        default_notify_channels=default_channels,
    )
