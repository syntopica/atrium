"""Register the `recall` subcommand on the atrium parser."""

from pathlib import Path

from atrium.cli_parser.sub_parsers import SubParsers
from atrium.commands.positive_limit import positive_limit


def add_recall_parser(subcommands: SubParsers, archive: Path, refresh_stamp: Path) -> None:
    """Register `recall` and its flags."""
    recall = subcommands.add_parser(
        "recall", help="Render this project's session-start recall block"
    )
    recall.add_argument(
        "--cwd",
        type=Path,
        default=Path.cwd(),
        help="Directory whose project to recall (default: the working directory)",
    )
    recall.add_argument("--limit", type=positive_limit, default=12)
    recall.add_argument("--archive", type=Path, default=archive)
    recall.add_argument("--refresh-stamp", type=Path, default=refresh_stamp)
