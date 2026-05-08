"""CLI subcommand: cronwatcher janitor — prune stale store entries."""
from __future__ import annotations

import argparse
import sys

from cronwatcher.config import load_config
from cronwatcher.janitor import run_janitor
from cronwatcher.job_store import JobStore


def cmd_janitor(args: argparse.Namespace) -> None:
    try:
        app_config = load_config(args.config)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    store = JobStore(app_config.store_path)
    known_names = [job.name for job in app_config.jobs]

    if args.dry_run:
        known_set = set(known_names)
        unknown = [n for n in store._data if n not in known_set]
        if unknown:
            print(f"Would remove {len(unknown)} unknown job(s): {', '.join(unknown)}")
        else:
            print("Dry-run: no unknown jobs found.")
        return

    result = run_janitor(
        store,
        known_names,
        max_age_days=args.max_age_days,
    )
    print(str(result))


def register_janitor_subcommand(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "janitor",
        help="Prune stale or unknown job records from the store.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be removed without making changes.",
    )
    p.add_argument(
        "--max-age-days",
        type=int,
        default=90,
        metavar="DAYS",
        help="Clear last_run timestamps older than DAYS (default: 90).",
    )
    p.set_defaults(func=cmd_janitor)
