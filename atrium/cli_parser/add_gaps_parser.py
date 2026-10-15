"""Register the `gaps` subcommand on the atrium parser."""

from atrium.cli_parser.sub_parsers import SubParsers
from atrium.commands.positive_limit import positive_limit


def add_gaps_parser(subcommands: SubParsers) -> None:
    """Register `gaps` and its flags."""
    gaps = subcommands.add_parser(
        "gaps",
        help="Report, from the query log, what was asked and not answered, and what was served",
    )
    gaps.add_argument("--days", type=positive_limit, default=14)
    gaps.add_argument("--top", type=positive_limit, default=25)
