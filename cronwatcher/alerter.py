"""Alert dispatchers for cronwatcher."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

from cronwatcher.config import AlertConfig
from cronwatcher.job_store import JobRecord

logger = logging.getLogger(__name__)


def _build_subject(record: JobRecord) -> str:
    return f"[cronwatcher] ALERT: job '{record.job_name}' failed"


def _build_body(record: JobRecord) -> str:
    lines = [
        f"Job '{record.job_name}' has failed.",
        f"Consecutive failures : {record.consecutive_failures}",
        f"Last exit code       : {record.last_exit_code}",
        f"Last run at          : {record.last_run_at}",
        "",
    ]
    if record.last_stderr:
        lines += ["--- stderr ---", record.last_stderr.strip(), ""]
    return "\n".join(lines)


def send_email_alert(
    record: JobRecord,
    cfg: AlertConfig,
    smtp_host: str = "localhost",
    smtp_port: int = 25,
    smtp_user: Optional[str] = None,
    smtp_password: Optional[str] = None,
) -> bool:
    """Send an e-mail alert.  Returns True on success."""
    if not cfg.email:
        logger.debug("No alert e-mail configured – skipping.")
        return False

    msg = EmailMessage()
    msg["Subject"] = _build_subject(record)
    msg["From"] = smtp_user or "cronwatcher@localhost"
    msg["To"] = cfg.email
    msg.set_content(_build_body(record))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.send_message(msg)
        logger.info("Alert e-mail sent to %s for job '%s'.", cfg.email, record.job_name)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send alert e-mail: %s", exc)
        return False


def log_alert(record: JobRecord) -> None:
    """Always-available fallback alert that writes to the log."""
    logger.warning(
        "ALERT | job='%s' consecutive_failures=%d exit_code=%s",
        record.job_name,
        record.consecutive_failures,
        record.last_exit_code,
    )
