"""Register the `search` subcommand on the atrium parser."""

from pathlib import Path

from atrium.cli_parser.sub_parsers import SubParsers
from atrium.commands.positive_limit import positive_limit


def add_search_parser(subcommands: SubParsers) -> None:
    """Register `search` and its flags."""
    search = subcommands.add_parser("search", help="Search the index")
    search.add_argument("query")
    search.add_argument("--limit", type=positive_limit, default=10)
    search.add_argument(
        "--project",
        type=Path,
        default=None,
        metavar="DIR",
        help="Restrict the search to the project containing DIR",
    )
    lanes = search.add_mutually_exclusive_group()
    lanes.add_argument(
        "--substring",
        action="store_true",
        help="Match fragments inside words instead of whole words",
    )
    lanes.add_argument("--words", action="store_true", help="Lexical lane only, no fusion")
    lanes.add_argument("--dense", action="store_true", help="Semantic lane only, no fusion")
