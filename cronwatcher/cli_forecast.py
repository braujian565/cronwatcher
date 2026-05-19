"""CLI subcommand: forecast — show predicted next-run times for all jobs."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from cronwatcher.config import AppConfig
from cronwatcher.forecast import compute_forecast, format_forecast_table


def cmd_forecast(args: argparse.Namespace) -> None:
    """Print a table of predicted next-run times."""
    try:
        app_config = AppConfig.load(args.config)
    except FileNotFoundError:
        print(f"[error] Config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    horizon_hours: int = getattr(args, "horizon", 24)
    now = datetime.now()

    entries = compute_forecast(app_config, now=now, horizon_hours=horizon_hours)

    if not entries:
        print("No jobs are scheduled to run within the next "
              f"{horizon_hours} hour(s).")
        return

    tag_filter: str | None = getattr(args, "tag", None)
    if tag_filter:
        entries = [e for e in entries if tag_filter in (e.job.tags or [])]
        if not entries:
            print(f"No jobs with tag '{tag_filter}' found in forecast.")
            return

    print(format_forecast_table(entries))


def register_forecast_subcommand(
    subparsers: argparse._SubParsersAction,  # type: ignore[type-arg]
) -> None:
    """Attach the *forecast* subcommand to an existing argument parser."""
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "forecast",
        help="Show predicted next-run times for scheduled jobs.",
    )
    parser.add_argument(
        "--horizon",
        type=int,
        default=24,
        metavar="HOURS",
        help="Look-ahead window in hours (default: 24).",
    )
    parser.add_argument(
        "--tag",
        default=None,
        metavar="TAG",
        help="Filter output to jobs carrying this tag.",
    )
    parser.set_defaults(func=cmd_forecast)
