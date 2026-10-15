"""Register the `remember` subcommand on the atrium parser."""

import argparse

from atrium.cli_parser.sub_parsers import SubParsers
from atrium.remember.remember_contract import REMEMBER_CONTRACT


def add_remember_parser(subcommands: SubParsers) -> None:
    """Register `remember` and its flags."""
    remember = subcommands.add_parser(
        "remember",
        help="Keep one statement in a project's memory, searchable at once",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=REMEMBER_CONTRACT,
    )
    remember.add_argument("--project", required=True, metavar="DIR")
    remember.add_argument(
        "--supersedes",
        action="append",
        default=[],
        metavar="RECORD_ID",
        help="An episode this statement replaces (repeatable)",
    )
