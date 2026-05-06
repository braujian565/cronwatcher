"""CLI sub-command: send-digest — trigger an immediate digest report."""

from __future__ import annotations

import logging

from cronwatcher.config import load_config
from cronwatcher.digest import build_digest, send_digest
from cronwatcher.job_store import JobStore

logger = logging.getLogger(__name__)


def cmd_send_digest(args) -> int:
    """Build and send a digest report, return exit code."""
    try:
        config = load_config(args.config)
    except FileNotFoundError as exc:
        logger.error("Config not found: %s", exc)
        return 1

    store = JobStore(config.state_file)
    report = build_digest(config, store)

    if args.dry_run:
        print(report.table)
        print(f"\n{report.summary_line()}")
        return 0

    send_digest(config, store)
    print(f"Digest sent — {report.summary_line()}")
    return 0


def register_digest_subcommand(subparsers) -> None:
    """Attach the send-digest sub-command to an existing subparsers group."""
    p = subparsers.add_parser(
        "send-digest",
        help="Send an immediate digest report of all job statuses",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print the digest to stdout instead of sending it",
    )
    p.set_defaults(func=cmd_send_digest)
