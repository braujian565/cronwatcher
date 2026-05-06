"""CLI sub-commands for the audit log: ``cronwatcher audit list``."""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronwatcher.audit import AuditEntry, AuditLog

_DEFAULT_AUDIT_PATH = "/var/lib/cronwatcher/audit.jsonl"
_DEFAULT_LIMIT = 20


def _format_entry(e: AuditEntry) -> str:
    status = "OK" if e.exit_code == 0 else f"FAIL({e.exit_code})"
    retries = f" retries={e.retries}" if e.retries else ""
    tags = f" [{', '.join(e.tags)}]" if e.tags else ""
    snippet = f"  stderr: {e.stderr_snippet}" if e.stderr_snippet else ""
    line = (
        f"{e.timestamp}  {e.job_name:<24} {status:<12}"
        f" {e.duration_seconds:>7.3f}s{retries}{tags}"
    )
    if snippet:
        line += f"\n    {snippet}"
    return line


def cmd_audit_list(args: argparse.Namespace) -> int:
    """Print recent audit entries, optionally filtered by job name."""
    log = AuditLog(args.audit_file)
    entries: List[AuditEntry] = log.read_all()

    if args.job:
        entries = [e for e in entries if e.job_name == args.job]

    if not entries:
        print("No audit entries found.")
        return 0

    # Most-recent first, limited
    entries = entries[-args.limit:][::-1]

    for entry in entries:
        print(_format_entry(entry))
    return 0


def register_audit_subcommand(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    audit_parser = subparsers.add_parser(
        "audit", help="View the job execution audit log"
    )
    audit_sub = audit_parser.add_subparsers(dest="audit_cmd")

    list_parser = audit_sub.add_parser("list", help="List recent audit entries")
    list_parser.add_argument(
        "--job", metavar="NAME", help="Filter by job name"
    )
    list_parser.add_argument(
        "--limit",
        type=int,
        default=_DEFAULT_LIMIT,
        metavar="N",
        help=f"Maximum entries to show (default: {_DEFAULT_LIMIT})",
    )
    list_parser.add_argument(
        "--audit-file",
        default=_DEFAULT_AUDIT_PATH,
        metavar="PATH",
        help="Path to audit JSONL file",
    )
    list_parser.set_defaults(func=cmd_audit_list)

    # If no sub-command given, fall back to list
    audit_parser.set_defaults(
        func=lambda a: (
            cmd_audit_list(a)
            if hasattr(a, "limit")
            else (audit_parser.print_help() or 0)
        )
    )
