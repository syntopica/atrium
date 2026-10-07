"""Register the `rekey-synthesis` subcommand on the atrium parser."""

from pathlib import Path

from atrium.cli_parser.sub_parsers import SubParsers


def add_rekey_synthesis_parser(subcommands: SubParsers, archive: Path) -> None:
    """Register `rekey-synthesis` and its flags."""
    rekey = subcommands.add_parser(
        "rekey-synthesis",
        help="Re-key the synthesis registry onto the schema 2 event id rule",
    )
    rekey.add_argument("--apply", action="store_true", help="Write; otherwise only report the plan")
    rekey.add_argument(
        "--repair",
        action="store_true",
        help="Ask the archive which rule each record's ids follow, rather than trusting its stamp",
    )
    rekey.add_argument("--archive", type=Path, default=archive)
