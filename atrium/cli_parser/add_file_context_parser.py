"""Register the `file-context` subcommand on the atrium parser."""

from pathlib import Path

from atrium.cli_parser.sub_parsers import SubParsers
from atrium.commands.positive_limit import positive_limit


def add_file_context_parser(subcommands: SubParsers) -> None:
    """Register `file-context` and its flags."""
    file_context = subcommands.add_parser(
        "file-context",
        help="Print, as JSON, this project's newest episodes that name one file",
    )
    file_context.add_argument("path", type=Path)
    file_context.add_argument("--limit", type=positive_limit, default=3)
