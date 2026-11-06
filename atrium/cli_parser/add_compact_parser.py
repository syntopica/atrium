"""Register the `compact` subcommand on the atrium parser."""

from atrium.cli_parser.sub_parsers import SubParsers


def add_compact_parser(subcommands: SubParsers) -> None:
    """Register `compact` and its flags."""
    compact = subcommands.add_parser(
        "compact",
        help="Rebuild both full-text lanes and VACUUM, reclaiming deleted rows' space",
    )
    compact.add_argument(
        "--apply", action="store_true", help="Compact; otherwise only report the file size"
    )
