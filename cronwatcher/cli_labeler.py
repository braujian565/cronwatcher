"""CLI sub-commands for managing job labels.

Sub-commands
------------
  label set   <job> <label>   -- assign a label
  label get   <job>           -- print current label
  label rm    <job>           -- remove a label
  label list                  -- list all labels
"""
from __future__ import annotations

import argparse
from pathlib import Path

from cronwatcher.labeler import Labeler


def _get_labeler(args: argparse.Namespace) -> Labeler:
    store_dir = Path(getattr(args, "store_dir", "."))
    return Labeler(path=store_dir / "cronwatcher_labels.json")


def cmd_label_set(args: argparse.Namespace) -> None:
    lb = _get_labeler(args)
    lb.set_label(args.job, args.label)
    print(f"Label set: {args.job!r} -> {args.label!r}")


def cmd_label_get(args: argparse.Namespace) -> None:
    lb = _get_labeler(args)
    label = lb.get_label(args.job)
    if label is None:
        print(f"No label set for {args.job!r}")
    else:
        print(f"{args.job}: {label}")


def cmd_label_rm(args: argparse.Namespace) -> None:
    lb = _get_labeler(args)
    removed = lb.remove_label(args.job)
    if removed:
        print(f"Label removed for {args.job!r}")
    else:
        print(f"No label found for {args.job!r}")


def cmd_label_list(args: argparse.Namespace) -> None:
    lb = _get_labeler(args)
    labels = lb.all_labels()
    if not labels:
        print("No labels defined.")
        return
    col = max(len(k) for k in labels)
    print(f"{'JOB':<{col}}  LABEL")
    print("-" * (col + 20))
    for job, label in sorted(labels.items()):
        print(f"{job:<{col}}  {label}")


def _dispatch(args: argparse.Namespace) -> None:
    actions = {
        "set": cmd_label_set,
        "get": cmd_label_get,
        "rm": cmd_label_rm,
        "list": cmd_label_list,
    }
    actions[args.label_action](args)


def register_labeler_subcommand(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("label", help="Manage human-readable job labels")
    sub = p.add_subparsers(dest="label_action", required=True)

    s = sub.add_parser("set", help="Assign a label to a job")
    s.add_argument("job", help="Job name")
    s.add_argument("label", help="Human-readable label")

    g = sub.add_parser("get", help="Print the label for a job")
    g.add_argument("job", help="Job name")

    r = sub.add_parser("rm", help="Remove a label from a job")
    r.add_argument("job", help="Job name")

    sub.add_parser("list", help="List all labels")

    p.set_defaults(func=_dispatch)
