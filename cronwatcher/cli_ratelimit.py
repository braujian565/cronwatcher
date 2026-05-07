"""CLI subcommand for inspecting and resetting alert rate limits."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronwatcher.ratelimit import RateLimiter

_DEFAULT_STORE = Path(".cronwatcher_ratelimit.json")
_DEFAULT_WINDOW = 3600.0
_DEFAULT_MAX = 5


def _get_limiter(args: argparse.Namespace) -> RateLimiter:
    store = Path(getattr(args, "ratelimit_store", _DEFAULT_STORE))
    return RateLimiter(store, window_seconds=_DEFAULT_WINDOW, max_alerts=_DEFAULT_MAX)


def cmd_ratelimit_list(args: argparse.Namespace) -> None:
    limiter = _get_limiter(args)
    entries = limiter.all_entries()
    if not entries:
        print("No rate limit entries recorded.")
        return
    print(f"{'JOB':<30} {'ALERTS IN WINDOW':>16} {'LIMITED':>8}")
    print("-" * 58)
    for entry in sorted(entries, key=lambda e: e.job_name):
        count = entry.count_in_window(limiter.window_seconds)
        limited = limiter.is_limited(entry.job_name)
        flag = "YES" if limited else "no"
        print(f"{entry.job_name:<30} {count:>16} {flag:>8}")


def cmd_ratelimit_reset(args: argparse.Namespace) -> None:
    limiter = _get_limiter(args)
    job = args.job
    limiter.reset(job)
    print(f"Rate limit history cleared for job: {job}")


def register_ratelimit_subcommand(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    parser = subparsers.add_parser("ratelimit", help="Manage alert rate limits")
    parser.add_argument(
        "--store",
        dest="ratelimit_store",
        default=str(_DEFAULT_STORE),
        help="Path to rate limit store file",
    )
    sub = parser.add_subparsers(dest="ratelimit_cmd")

    sub.add_parser("list", help="List current rate limit state for all jobs")

    reset_p = sub.add_parser("reset", help="Reset rate limit history for a job")
    reset_p.add_argument("job", help="Job name to reset")

    parser.set_defaults(func=_dispatch)


def _dispatch(args: argparse.Namespace) -> None:
    if args.ratelimit_cmd == "list":
        cmd_ratelimit_list(args)
    elif args.ratelimit_cmd == "reset":
        cmd_ratelimit_reset(args)
    else:
        print("Specify a subcommand: list, reset", file=sys.stderr)
        sys.exit(1)
