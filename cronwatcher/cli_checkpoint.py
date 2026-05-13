"""CLI subcommands for inspecting and managing job checkpoints."""
from __future__ import annotations

import argparse
from datetime import timezone
from typing import Optional

from cronwatcher.checkpoint import Checkpointer


def _get_checkpointer(args: argparse.Namespace) -> Checkpointer:
    checkpoint_dir = getattr(args, "checkpoint_dir", ".cronwatcher/checkpoints")
    return Checkpointer(checkpoint_dir)


def cmd_checkpoint_list(args: argparse.Namespace) -> None:
    cp = _get_checkpointer(args)
    entries = cp.all_entries()
    if not entries:
        print("No checkpoints found.")
        return
    header = f"{'JOB':<30} {'LAST SUCCESS':<30} {'AGE (s)':>10}"
    print(header)
    print("-" * len(header))
    for e in entries:
        age = f"{e.age_seconds():.0f}"
        ts = e.last_success.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"{e.job_name:<30} {ts:<30} {age:>10}")


def cmd_checkpoint_show(args: argparse.Namespace) -> None:
    cp = _get_checkpointer(args)
    entry = cp.load(args.job)
    if entry is None:
        print(f"No checkpoint found for job: {args.job}")
        return
    ts = entry.last_success.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"Job          : {entry.job_name}")
    print(f"Last success : {ts}")
    print(f"Age (s)      : {entry.age_seconds():.0f}")


def cmd_checkpoint_delete(args: argparse.Namespace) -> None:
    cp = _get_checkpointer(args)
    removed = cp.delete(args.job)
    if removed:
        print(f"Checkpoint deleted for job: {args.job}")
    else:
        print(f"No checkpoint found for job: {args.job}")


def _dispatch(args: argparse.Namespace) -> None:
    sub = getattr(args, "checkpoint_sub", None)
    if sub == "list":
        cmd_checkpoint_list(args)
    elif sub == "show":
        cmd_checkpoint_show(args)
    elif sub == "delete":
        cmd_checkpoint_delete(args)
    else:
        print("Use a subcommand: list | show | delete")


def register_checkpoint_subcommand(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("checkpoint", help="Manage job checkpoints")
    p.add_argument("--checkpoint-dir", default=".cronwatcher/checkpoints",
                   help="Directory where checkpoints are stored")
    subs = p.add_subparsers(dest="checkpoint_sub")

    subs.add_parser("list", help="List all checkpoints")

    show_p = subs.add_parser("show", help="Show checkpoint for a specific job")
    show_p.add_argument("job", help="Job name")

    del_p = subs.add_parser("delete", help="Delete checkpoint for a specific job")
    del_p.add_argument("job", help="Job name")

    p.set_defaults(func=_dispatch)
