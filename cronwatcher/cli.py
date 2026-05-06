"""Command-line interface for cronwatcher daemon."""

import argparse
import logging
import sys
import time
from pathlib import Path

from cronwatcher.config import load_config
from cronwatcher.job_store import JobStore
from cronwatcher.scheduler import get_due_jobs
from cronwatcher.watcher import Watcher

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=level,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwatcher",
        description="Lightweight daemon that monitors cron job execution and sends alerts on failures.",
    )
    parser.add_argument(
        "-c",
        "--config",
        default="cronwatcher/config.example.yaml",
        help="Path to the YAML configuration file (default: cronwatcher/config.example.yaml)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("run", help="Run the cronwatcher daemon loop")
    subparsers.add_parser("check", help="Perform a single pass and exit")
    subparsers.add_parser("list", help="List configured jobs and exit")

    return parser


def cmd_list(config_path: str) -> None:
    config = load_config(config_path)
    print(f"{'NAME':<24} {'SCHEDULE':<20} {'COMMAND'}")
    print("-" * 70)
    for job in config.jobs:
        print(f"{job.name:<24} {job.schedule:<20} {job.command}")


def cmd_check(config_path: str) -> None:
    config = load_config(config_path)
    store = JobStore(config.store_path)
    watcher = Watcher(config, store)
    due = get_due_jobs(config)
    if not due:
        logger.info("No jobs due right now.")
        return
    logger.info("Running %d due job(s)...", len(due))
    for job in due:
        watcher.run_job(job)


def cmd_run(config_path: str) -> None:
    config = load_config(config_path)
    store = JobStore(config.store_path)
    watcher = Watcher(config, store)
    logger.info("cronwatcher daemon started. Polling every 60 seconds.")
    try:
        while True:
            watcher.run_all()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("cronwatcher stopped.")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.verbose)

    command = args.command or "run"

    if not Path(args.config).exists():
        parser.error(f"Config file not found: {args.config}")

    if command == "list":
        cmd_list(args.config)
    elif command == "check":
        cmd_check(args.config)
    else:
        cmd_run(args.config)

    return 0


if __name__ == "__main__":
    sys.exit(main())
