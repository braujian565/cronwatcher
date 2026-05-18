"""CLI sub-commands for managing concurrency limits.

Subcommands:
  concurrency list               – show all limits and current slot usage
  concurrency set <name> <max>   – create or update a limit
  concurrency release <name> <job> – manually release a stuck slot
  concurrency remove <name>      – delete a limit entirely
"""
from __future__ import annotations

import argparse
from pathlib import Path

from cronwatcher.concurrency import ConcurrencyManager, DEFAULT_STORE


def _get_manager(args: argparse.Namespace) -> ConcurrencyManager:
    path = Path(getattr(args, "store", None) or DEFAULT_STORE)
    return ConcurrencyManager(store_path=path)


def cmd_concurrency_list(args: argparse.Namespace) -> None:
    mgr = _get_manager(args)
    limits = mgr.all_limits()
    if not limits:
        print("No concurrency limits configured.")
        return
    header = f"{'NAME':<25} {'MAX':>5} {'RUNNING':>9} {'SLOTS FREE':>11}"
    print(header)
    print("-" * len(header))
    for lim in sorted(limits, key=lambda l: l.name):
        free = lim.max_running - len(lim.running)
        running_str = ", ".join(lim.running) if lim.running else "-"
        print(f"{lim.name:<25} {lim.max_running:>5} {running_str:>9} {free:>11}")


def cmd_concurrency_set(args: argparse.Namespace) -> None:
    mgr = _get_manager(args)
    if args.max < 1:
        print(f"Error: max must be a positive integer, got {args.max}.")
        return
    mgr.set_limit(args.name, args.max)
    print(f"Concurrency limit '{args.name}' set to {args.max}.")


def cmd_concurrency_release(args: argparse.Namespace) -> None:
    mgr = _get_manager(args)
    try:
        mgr.release(args.name, args.job)
    except KeyError as exc:
        print(f"Error: {exc}")
        return
    print(f"Released slot for job '{args.job}' in limit '{args.name}'.")


def cmd_concurrency_remove(args: argparse.Namespace) -> None:
    mgr = _get_manager(args)
    removed = mgr.remove(args.name)
    if removed:
        print(f"Concurrency limit '{args.name}' removed.")
    else:
        print(f"No limit named '{args.name}' found.")


def _dispatch(args: argparse.Namespace) -> None:
    mapping = {
        "list": cmd_concurrency_list,
        "set": cmd_concurrency_set,
        "release": cmd_concurrency_release,
        "remove": cmd_concurrency_remove,
    }
    mapping[args.concurrency_cmd](args)


def register_concurrency_subcommand(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("concurrency", help="Manage job concurrency limits")
    sub = p.add_subparsers(dest="concurrency_cmd", required=True)

    sub.add_parser("list", help="List all concurrency limits")

    p_set = sub.add_parser("set", help="Create or update a limit")
    p_set.add_argument("name", help="Limit bucket name")
    p_set.add_argument("max", type=int, help="Maximum concurrent slots")

    p_rel = sub.add_parser("release", help="Manually release a stuck job slot")
    p_rel.add_argument("name", help="Limit bucket name")
    p_rel.add_argument("job", help="Job name to release")

    p_rm = sub.add_parser("remove", help="Remove a limit entirely")
    p_rm.add_argument("name", help
