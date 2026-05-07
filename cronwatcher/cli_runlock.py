"""CLI sub-commands for inspecting and clearing run-locks."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronwatcher.runlock import RunLock

_DEFAULT_LOCK_DIR = Path("/tmp/cronwatcher/locks")


def _get_lock(args: argparse.Namespace) -> RunLock:
    lock_dir = Path(getattr(args, "lock_dir", None) or _DEFAULT_LOCK_DIR)
    return RunLock(lock_dir)


def cmd_runlock_list(args: argparse.Namespace) -> None:
    rl = _get_lock(args)
    files = sorted(rl.lock_dir.glob("*.lock"))
    if not files:
        print("No active locks.")
        return

    print(f"{'JOB':<30} {'PID':>8}  {'LOCKED':>6}  STARTED")
    print("-" * 62)
    for f in files:
        entry = rl.current_entry(f.stem)
        if entry is None:
            continue
        locked = not entry.is_stale()
        import datetime
        started = datetime.datetime.fromtimestamp(entry.started_at).strftime("%Y-%m-%d %H:%M:%S")
        print(f"{entry.job_name:<30} {entry.pid:>8}  {'yes' if locked else 'stale':>6}  {started}")


def cmd_runlock_clear(args: argparse.Namespace) -> None:
    rl = _get_lock(args)
    job: str = args.job
    if not rl._path(job).exists():
        print(f"No lock found for job '{job}'.")
        sys.exit(1)
    rl.release(job)
    print(f"Lock cleared for job '{job}'.")


def register_runlock_subcommand(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    parser = subparsers.add_parser("runlock", help="Manage job run-locks")
    parser.add_argument(
        "--lock-dir",
        default=str(_DEFAULT_LOCK_DIR),
        help="Directory where lock files are stored",
    )
    sub = parser.add_subparsers(dest="runlock_cmd", required=True)

    sub.add_parser("list", help="List active run-locks")

    clear_p = sub.add_parser("clear", help="Force-clear a lock for a job")
    clear_p.add_argument("job", help="Job name whose lock to clear")

    parser.set_defaults(func=_dispatch)


def _dispatch(args: argparse.Namespace) -> None:
    if args.runlock_cmd == "list":
        cmd_runlock_list(args)
    elif args.runlock_cmd == "clear":
        cmd_runlock_clear(args)
