"""Register the `ingest-notes` subcommand on the atrium parser."""

from pathlib import Path

from atrium.cli_parser.sub_parsers import SubParsers


def add_ingest_notes_parser(subcommands: SubParsers) -> None:
    """Register `ingest-notes` and its flags."""
    notes = subcommands.add_parser("ingest-notes", help="Index a tree of curated markdown notes")
    notes.add_argument("root", type=Path)
    notes.add_argument("--provider", default="brain")
    notes.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="DIR",
        help="Directory name to skip anywhere under the root (repeatable)",
    )
    notes.add_argument(
        "--partial",
        action="store_true",
        help="The root is a slice of the provider's notes: skip the sweep that "
        "removes notes absent from it",
    )
    notes.add_argument(
        "--third-party",
        action="store_true",
        help="The tree is saved third-party content, not the user's own words: "
        "records are marked role 'source', stay lexically searchable, and are "
        "never embedded or injected at session start",
    )
