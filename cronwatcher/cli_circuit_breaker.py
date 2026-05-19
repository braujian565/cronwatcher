"""CLI subcommand for inspecting and managing circuit breaker state."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from cronwatcher.circuit_breaker import CircuitBreaker

_DEFAULT_STORE = Path(".cronwatcher/circuit_breaker.json")


def _get_breaker(args: argparse.Namespace) -> CircuitBreaker:
    store = Path(getattr(args, "store", None) or _DEFAULT_STORE)
    return CircuitBreaker(store_path=store)


def cmd_circuit_list(args: argparse.Namespace) -> None:
    breaker = _get_breaker(args)
    states = breaker._states
    if not states:
        print("No circuit breaker state recorded.")
        return
    header = f"{'JOB':<30} {'FAILURES':>8} {'STATUS':<12} {'OPENED AT'}"
    print(header)
    print("-" * len(header))
    for job_name, state in sorted(states.items()):
        if state.is_open:
            status = "HALF-OPEN" if state.is_half_open else "OPEN"
            opened = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(state.opened_at))
        else:
            status = "CLOSED"
            opened = "-"
        print(f"{job_name:<30} {state.failure_count:>8} {status:<12} {opened}")


def cmd_circuit_reset(args: argparse.Namespace) -> None:
    breaker = _get_breaker(args)
    job_name: str = args.job
    if job_name not in breaker._states:
        print(f"No circuit state found for job: {job_name}", file=sys.stderr)
        sys.exit(1)
    breaker.reset(job_name)
    print(f"Circuit breaker reset for job: {job_name}")


def register_circuit_breaker_subcommand(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("circuit", help="Manage circuit breaker state")
    p.add_argument("--store", default=str(_DEFAULT_STORE), help="Path to circuit breaker state file")
    sub = p.add_subparsers(dest="circuit_cmd", required=True)

    sub.add_parser("list", help="List circuit breaker states")

    reset_p = sub.add_parser("reset", help="Reset circuit breaker for a job")
    reset_p.add_argument("job", help="Job name to reset")

    p.set_defaults(func=_dispatch)


def _dispatch(args: argparse.Namespace) -> None:
    if args.circuit_cmd == "list":
        cmd_circuit_list(args)
    elif args.circuit_cmd == "reset":
        cmd_circuit_reset(args)
