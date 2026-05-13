"""CLI sub-command: watchdog — list jobs that appear stuck."""
from __future__ import annotations

import argparse
import sys

from cronwatcher.config import load_config
from cronwatcher.runlock import RunLock
from cronwatcher.watchdog import check_stuck_jobs

_DEFAULT_LOCK_DIR = "/tmp/cronwatcher/locks"
_DEFAULT_WARN_AFTER = 3600


def cmd_watchdog(args: argparse.Namespace) -> None:
    try:
        app_config = load_config(args.config)
    except FileNotFoundError:
        print(f"Config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    lock_dir = getattr(args, "lock_dir", _DEFAULT_LOCK_DIR)
    warn_after = getattr(args, "warn_after", _DEFAULT_WARN_AFTER)
    lock = RunLock(lock_dir=lock_dir)

    stuck = check_stuck_jobs(app_config, lock, default_warn_after=warn_after)

    if not stuck:
        print("No stuck jobs detected.")
        return

    print(f"{'JOB':<30} {'PID':>7} {'RUNNING':>12} {'LIMIT':>8}")
    print("-" * 62)
    for s in stuck:
        limit = str(s.timeout_seconds) + "s" if s.timeout_seconds else "default"
        print(
            f"{s.job_name:<30} {s.pid:>7} {s.running_seconds:>10.0f}s {limit:>8}"
        )


def register_watchdog_subcommand(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("watchdog", help="List jobs that appear stuck (exceeded timeout)")
    p.add_argument(
        "--lock-dir",
        default=_DEFAULT_LOCK_DIR,
        help="Directory used by RunLock (default: %(default)s)",
    )
    p.add_argument(
        "--warn-after",
        type=int,
        default=_DEFAULT_WARN_AFTER,
        metavar="SECONDS",
        help="Seconds before a job is considered stuck when no timeout is configured (default: %(default)s)",
    )
    p.set_defaults(func=cmd_watchdog)
