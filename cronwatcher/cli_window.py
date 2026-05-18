"""CLI subcommand: cronwatcher window — inspect execution windows."""
from __future__ import annotations

import argparse
from datetime import datetime
from typing import List

from cronwatcher.config import AppConfig
from cronwatcher.window import WindowPolicy, build_window_policy


def _policies_from_config(cfg: AppConfig) -> List[WindowPolicy]:
    policies = []
    for job in cfg.jobs:
        raw = getattr(job, "windows", None) or []
        policies.append(build_window_policy(job.name, raw))
    return policies


def cmd_window_list(args: argparse.Namespace) -> None:
    """List all jobs and their configured execution windows."""
    try:
        cfg = AppConfig.load(args.config)
    except FileNotFoundError:
        print(f"Config file not found: {args.config}")
        return

    policies = _policies_from_config(cfg)
    if not policies:
        print("No jobs configured.")
        return

    now = datetime.now()
    print(f"{'JOB':<30} {'WINDOWS':<30} {'ALLOWED NOW':<12}")
    print("-" * 74)
    for p in policies:
        windows_str = ", ".join(str(w) for w in p.windows) if p.windows else "(any time)"
        allowed = "yes" if p.is_allowed(now) else "no"
        print(f"{p.job_name:<30} {windows_str:<30} {allowed:<12}")


def cmd_window_check(args: argparse.Namespace) -> None:
    """Check whether a specific job is allowed to run right now."""
    try:
        cfg = AppConfig.load(args.config)
    except FileNotFoundError:
        print(f"Config file not found: {args.config}")
        return

    job = next((j for j in cfg.jobs if j.name == args.job), None)
    if job is None:
        print(f"Unknown job: {args.job}")
        return

    raw = getattr(job, "windows", None) or []
    policy = build_window_policy(job.name, raw)
    now = datetime.now()
    if policy.is_allowed(now):
        print(f"{args.job}: allowed at {now.strftime('%H:%M')}")
    else:
        print(f"{args.job}: BLOCKED at {now.strftime('%H:%M')}")


def register_window_subcommand(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser("window", help="Inspect execution windows")
    sp = p.add_subparsers(dest="window_cmd")

    sp.add_parser("list", help="List windows for all jobs")

    chk = sp.add_parser("check", help="Check if a job is allowed now")
    chk.add_argument("job", help="Job name")

    def _dispatch(args: argparse.Namespace) -> None:
        if args.window_cmd == "list":
            cmd_window_list(args)
        elif args.window_cmd == "check":
            cmd_window_check(args)
        else:
            p.print_help()

    p.set_defaults(func=_dispatch)
