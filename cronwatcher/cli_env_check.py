"""CLI subcommand: ``cronwatcher env-check``

Prints a report of jobs whose required environment variables are
missing or empty.  Exits with code 1 if any problems are found.
"""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronwatcher.config import AppConfig, load_config
from cronwatcher.env_check import EnvCheckResult, check_all_envs


def cmd_env_check(args: argparse.Namespace) -> None:
    """Entry point for the env-check subcommand."""
    try:
        cfg: AppConfig = load_config(args.config)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)

    jobs = cfg.jobs
    if args.tags:
        wanted = set(args.tags)
        jobs = [j for j in jobs if wanted.intersection(getattr(j, "tags", None) or [])]

    failures: List[EnvCheckResult] = check_all_envs(jobs)

    if not failures:
        print(f"All {len(jobs)} job(s) passed env checks.")
        return

    print(f"{len(failures)} job(s) have env problems:\n")
    for result in failures:
        print(f"  {result}")
        if result.missing:
            for var in result.missing:
                print(f"    [MISSING] {var}")
        if result.empty:
            for var in result.empty:
                print(f"    [EMPTY]   {var}")

    sys.exit(1)


def register_env_check_subcommand(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "env-check",
        help="Verify required environment variables are set for all jobs.",
    )
    parser.add_argument(
        "--tags",
        nargs="+",
        metavar="TAG",
        help="Limit check to jobs carrying these tags.",
    )
    parser.set_defaults(func=cmd_env_check)
