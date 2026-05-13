"""CLI subcommand: cronwatcher variance

Prints a table of runtime variance for all tracked jobs, highlighting
any jobs whose last run deviated significantly from their average.
"""
from __future__ import annotations

import argparse
import sys

from cronwatcher.config import AppConfig
from cronwatcher.job_store import JobStore
from cronwatcher.variance import check_all_variances


def cmd_variance(args: argparse.Namespace) -> None:
    try:
        cfg = AppConfig.load(args.config)
    except FileNotFoundError:
        print(f"Config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    store = JobStore(cfg.store_path)
    threshold = args.threshold
    reports = check_all_variances(store, threshold_z=threshold)

    if not reports:
        print("No job history found.")
        return

    header = f"{'JOB':<30} {'LAST':>8} {'AVG':>8} {'STD':>8} {'Z':>7}  FLAG"
    print(header)
    print("-" * len(header))

    for r in reports:
        if r.avg_duration is None:
            print(f"{r.job_name:<30} {'N/A':>8} {'N/A':>8} {'N/A':>8} {'N/A':>7}")
            continue
        flag = "[!]" if r.flagged else ""
        print(
            f"{r.job_name:<30} "
            f"{r.last_duration:>8.1f} "
            f"{r.avg_duration:>8.1f} "
            f"{r.std_dev:>8.1f} "
            f"{r.z_score:>7.2f}  {flag}"
        )

    flagged = [r for r in reports if r.flagged]
    if flagged:
        print(f"\n{len(flagged)} job(s) flagged (|z| >= {threshold}).")
        if args.fail_on_flag:
            sys.exit(2)


def register_variance_subcommand(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser(
        "variance",
        help="Show runtime variance for all tracked jobs",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=2.0,
        metavar="Z",
        help="Z-score threshold to flag a job (default: 2.0)",
    )
    p.add_argument(
        "--fail-on-flag",
        action="store_true",
        default=False,
        help="Exit with code 2 if any jobs are flagged",
    )
    p.set_defaults(func=cmd_variance)
