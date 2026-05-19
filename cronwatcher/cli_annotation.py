"""CLI sub-commands for job annotations."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronwatcher.annotation import Annotation, Annotator

_DEFAULT_STORE = Path("cronwatcher_annotations.json")


def _get_annotator(args: argparse.Namespace) -> Annotator:
    store_path = Path(getattr(args, "annotation_store", _DEFAULT_STORE))
    return Annotator(store_path)


def cmd_annotation_add(args: argparse.Namespace) -> None:
    annotator = _get_annotator(args)
    annotation = Annotation(
        job_name=args.job,
        note=args.note,
        author=getattr(args, "author", "system"),
    )
    annotator.add(annotation)
    print(f"Annotation added to '{args.job}'.")


def cmd_annotation_list(args: argparse.Namespace) -> None:
    annotator = _get_annotator(args)
    job = getattr(args, "job", None)
    if job:
        names = [job]
    else:
        names = annotator.all_job_names()

    if not names:
        print("No annotations found.")
        return

    for name in names:
        entries = annotator.get(name)
        for entry in entries:
            print(f"[{entry.created_at}] {name} ({entry.author}): {entry.note}")


def cmd_annotation_clear(args: argparse.Namespace) -> None:
    annotator = _get_annotator(args)
    removed = annotator.delete_all(args.job)
    print(f"Removed {removed} annotation(s) for '{args.job}'.")


def register_annotation_subcommand(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    parser = subparsers.add_parser("annotation", help="Manage job annotations")
    sub = parser.add_subparsers(dest="annotation_cmd")

    add_p = sub.add_parser("add", help="Add an annotation to a job")
    add_p.add_argument("job", help="Job name")
    add_p.add_argument("note", help="Annotation text")
    add_p.add_argument("--author", default="system", help="Author name")
    add_p.set_defaults(func=cmd_annotation_add)

    list_p = sub.add_parser("list", help="List annotations")
    list_p.add_argument("--job", default=None, help="Filter by job name")
    list_p.set_defaults(func=cmd_annotation_list)

    clear_p = sub.add_parser("clear", help="Remove all annotations for a job")
    clear_p.add_argument("job", help="Job name")
    clear_p.set_defaults(func=cmd_annotation_clear)

    def _dispatch(args: argparse.Namespace) -> None:
        if not args.annotation_cmd:
            parser.print_help()
            sys.exit(1)
        args.func(args)

    parser.set_defaults(func=_dispatch)
