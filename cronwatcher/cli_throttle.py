"""CLI sub-commands for inspecting and managing alert throttle state."""

from __future__ import annotations

import argparse
from pathlib import Path

from cronwatcher.throttle import Throttler


_DEFAULT_STATE = Path(".cronwatcher/throttle.json")


def _get_throttler(args: argparse.Namespace) -> Throttler:
    state_path = Path(getattr(args, "state", None) or _DEFAULT_STATE)
    cooldown = getattr(args, "cooldown", 3600)
    return Throttler(state_path=state_path, cooldown_seconds=cooldown)


def cmd_throttle_list(args: argparse.Namespace) -> None:
    """Print all current throttle entries."""
    throttler = _get_throttler(args)
    entries = list(throttler._entries.values())
    if not entries:
        print("No throttle entries.")
        return
    fmt = "{:<30} {:>20} {:>8}"
    print(fmt.format("JOB", "LAST_ALERTED_AT", "COUNT"))
    print("-" * 62)
    import datetime
    for e in sorted(entries, key=lambda x: x.job_name):
        ts = datetime.datetime.fromtimestamp(e.last_alerted_at).isoformat(timespec="seconds")
        print(fmt.format(e.job_name, ts, e.alert_count))


def cmd_throttle_reset(args: argparse.Namespace) -> None:
    """Reset throttle state for a specific job (or all jobs)."""
    throttler = _get_throttler(args)
    if args.job == "--all":
        job_names = list(throttler._entries.keys())
        for name in job_names:
            throttler.reset(name)
        print(f"Reset throttle for {len(job_names)} job(s).")
    else:
        throttler.reset(args.job)
        print(f"Throttle reset for '{args.job}'.")


def register_throttle_subcommand(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--state", default=str(_DEFAULT_STATE), help="Path to throttle state file")
    common.add_argument("--cooldown", type=int, default=3600, help="Cooldown in seconds")

    throttle_parser = subparsers.add_parser("throttle", help="Manage alert throttle state")
    throttle_sub = throttle_parser.add_subparsers(dest="throttle_cmd")

    throttle_sub.add_parser("list", parents=[common], help="List throttle entries")

    reset_p = throttle_sub.add_parser("reset", parents=[common], help="Reset throttle for a job")
    reset_p.add_argument("job", help="Job name to reset, or --all")

    throttle_parser.set_defaults(func=_dispatch)


def _dispatch(args: argparse.Namespace) -> None:
    if args.throttle_cmd == "list":
        cmd_throttle_list(args)
    elif args.throttle_cmd == "reset":
        cmd_throttle_reset(args)
    else:
        print("Usage: cronwatcher throttle {list,reset}")
