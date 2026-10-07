"""Register the `record-session` subcommand on the atrium parser."""

import argparse

from atrium.cli_parser.sub_parsers import SubParsers
from atrium.session.record_session_contract import RECORD_SESSION_CONTRACT


def add_record_session_parser(subcommands: SubParsers) -> None:
    """Register `record-session` and its flags."""
    record_session = subcommands.add_parser(
        "record-session",
        help="Write the running session's own synthesis for a frozen checkpoint",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=RECORD_SESSION_CONTRACT,
    )
    record_session.add_argument("--checkpoint", required=True, metavar="ID")
    record_session.add_argument(
        "--nothing-durable",
        action="store_true",
        help="Consume the checkpoint without a record: the interval produced nothing to keep",
    )
