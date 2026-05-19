"""CLI subcommand: `cronwatcher backoff` — inspect effective back-off policy."""
from __future__ import annotations

import argparse
import sys
from typing import Optional

from cronwatcher.backoff import resolve_backoff
from cronwatcher.config import load_config


def cmd_backoff(args: argparse.Namespace) -> None:
    """Print the effective back-off policy for one or all jobs."""
    try:
        app_config = load_config(args.config)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    jobs = app_config.jobs
    if args.job:
        jobs = [j for j in jobs if j.name == args.job]
        if not jobs:
            print(f"error: job '{args.job}' not found", file=sys.stderr)
            sys.exit(1)

    col_w = max((len(j.name) for j in jobs), default=4)
    header = f"{'JOB':<{col_w}}  {'BASE':>8}  {'MULT':>6}  {'MAX':>8}  JITTER"
    print(header)
    print("-" * len(header))
    for job in jobs:
        policy = resolve_backoff(app_config, job)
        print(
            f"{job.name:<{col_w}}  "
            f"{policy.base_seconds:>8.1f}  "
            f"{policy.multiplier:>6.2f}  "
            f"{policy.max_seconds:>8.1f}  "
            f"{str(policy.jitter).lower()}"
        )


def register_backoff_subcommand(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "backoff",
        help="Show effective back-off policy for jobs",
    )
    parser.add_argument(
        "--job",
        metavar="NAME",
        default=None,
        help="Filter to a specific job name",
    )
    parser.set_defaults(func=cmd_backoff)
