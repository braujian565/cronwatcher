"""Notification channel registry and dispatcher for cronwatcher."""

from __future__ import annotations

import logging
from typing import Callable, Dict, List

from cronwatcher.alerter import log_alert, send_email_alert
from cronwatcher.config import AlertConfig
from cronwatcher.job_store import JobRecord

logger = logging.getLogger(__name__)

# Type alias for a notification handler
NotifyHandler = Callable[[JobRecord, AlertConfig], None]

_REGISTRY: Dict[str, NotifyHandler] = {}


def register(channel: str) -> Callable[[NotifyHandler], NotifyHandler]:
    """Decorator to register a notification handler for a named channel."""

    def decorator(fn: NotifyHandler) -> NotifyHandler:
        _REGISTRY[channel] = fn
        logger.debug("Registered notification channel: %s", channel)
        return fn

    return decorator


@register("email")
def _email_handler(record: JobRecord, alert_cfg: AlertConfig) -> None:
    send_email_alert(record, alert_cfg)


@register("log")
def _log_handler(record: JobRecord, alert_cfg: AlertConfig) -> None:  # noqa: ARG001
    log_alert(record)


def get_channels() -> List[str]:
    """Return the names of all registered notification channels."""
    return list(_REGISTRY.keys())


def dispatch(record: JobRecord, alert_cfg: AlertConfig, channels: List[str]) -> None:
    """Dispatch an alert to every requested channel.

    Unknown channel names are logged as warnings and skipped.
    """
    for channel in channels:
        handler = _REGISTRY.get(channel)
        if handler is None:
            logger.warning("Unknown notification channel %r — skipping.", channel)
            continue
        try:
            handler(record, alert_cfg)
        except Exception:  # pylint: disable=broad-except
            logger.exception("Error dispatching alert via channel %r", channel)
