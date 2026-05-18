"""CLI subcommands for managing per-job run quotas."""
from __future__ import annotations

import argparse
from typing import Optional

from cronwatcher.quota import QuotaManager, DEFAULT_QUOTA_FILE


def _get_manager(args: argparse.Namespace) -> QuotaManager:
    path = getattr(args, "quota_file", DEFAULT_QUOTA_FILE)
    return QuotaManager(store_path=path)


def cmd_quota_list(args: argparse.Namespace) -> None:
    mgr = _get_manager(args)
    entries = mgr.all_entries()
    if not entries:
        print("No quotas configured.")
        return
    header = f"{'JOB':<30} {'MAX RUNS':>8} {'WINDOW (s)':>10} {'USED':>6} {'EXCEEDED':>8}"
    print(header)
    print("-" * len(header))
    for e in sorted(entries, key=lambda x: x.job_name):
        used = e.count_in_window()
        exceeded = "YES" if e.is_exceeded() else "no"
        print(f"{e.job_name:<30} {e.max_runs:>8} {e.window_seconds:>10} {used:>6} {exceeded:>8}")


def cmd_quota_set(args: argparse.Namespace) -> None:
    mgr = _get_manager(args)
    mgr.set_quota(args.job, args.max_runs, args.window_seconds)
    print(
        f"Quota set: {args.job} → {args.max_runs} runs per {args.window_seconds}s window."
    )


def cmd_quota_reset(args: argparse.Namespace) -> None:
    mgr = _get_manager(args)
    entry = mgr.get_entry(args.job)
    if entry is None:
        print(f"No quota found for job: {args.job}")
        return
    entry.timestamps.clear()
    mgr._save()  # noqa: SLF001
    print(f"Quota counters reset for job: {args.job}")


def cmd_quota_remove(args: argparse.Namespace) -> None:
    mgr = _get_manager(args)
    removed = mgr.remove(args.job)
    if removed:
        print(f"Quota removed for job: {args.job}")
    else:
        print(f"No quota found for job: {args.job}")


def register_quota_subcommand(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    p = subparsers.add_parser("quota", help="Manage per-job run quotas")
    p.add_argument("--quota-file", default=DEFAULT_QUOTA_FILE, help="Path to quota store")
    sub = p.add_subparsers(dest="quota_cmd", required=True)

    sub.add_parser("list", help="List all quotas")

    p_set = sub.add_parser("set", help="Set a quota for a job")
    p_set.add_argument("job", help="Job name")
    p_set.add_argument("max_runs", type=int, help="Maximum runs allowed")
    p_set.add_argument("window_seconds", type=int, help="Time window in seconds")

    p_reset = sub.add_parser("reset", help="Reset run counter for a job")
    p_reset.add_argument("job", help="Job name")

    p_rm = sub.add_parser("remove", help="Remove quota for a job")
    p_rm.add_argument("job", help="Job name")

    p.set_defaults(func=_dispatch)


def _dispatch(args: argparse.Namespace) -> None:
    cmds = {
        "list": cmd_quota_list,
        "set": cmd_quota_set,
        "reset": cmd_quota_reset,
        "remove": cmd_quota_remove,
    }
    cmds[args.quota_cmd](args)
