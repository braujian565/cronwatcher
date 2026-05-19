"""CLI sub-command: forecast — show upcoming job run times."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime

from cronwatcher.config import load_config
from cronwatcher.forecast import compute_forecast, format_forecast_table


def cmd_forecast(args: argparse.Namespace) -> None:
    try:
        app_config = load_config(args.config)
    except FileNotFoundError:
        print(f"Config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    after: datetime | None = None
    if args.at:
        try:
            after = datetime.strptime(args.at, "%Y-%m-%dT%H:%M")
        except ValueError:
            print("--at must be in ISO format: YYYY-MM-DDTHH:MM", file=sys.stderr)
            sys.exit(1)

    entries = compute_forecast(
        app_config,
        after=after,
        horizon_minutes=args.horizon,
    )

    if args.job:
        entries = [e for e in entries if e.job_name == args.job]

    print(format_forecast_table(entries))


def register_forecast_subcommand(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("forecast", help="Show upcoming scheduled run times")
    p.add_argument(
        "--horizon",
        type=int,
        default=1440,
        metavar="MINUTES",
        help="How many minutes ahead to scan (default: 1440 = 24 h)",
    )
    p.add_argument(
        "--at",
        default=None,
        metavar="YYYY-MM-DDTHH:MM",
        help="Treat this timestamp as 'now' (useful for testing)",
    )
    p.add_argument(
        "--job",
        default=None,
        metavar="JOB_NAME",
        help="Filter output to a single job",
    )
    p.set_defaults(func=cmd_forecast)
