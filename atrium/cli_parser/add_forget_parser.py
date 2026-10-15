"""Register the `forget` subcommand on the atrium parser."""

from atrium.cli_parser.sub_parsers import SubParsers


def add_forget_parser(subcommands: SubParsers) -> None:
    """Register `forget` and its flags."""
    forget = subcommands.add_parser(
        "forget",
        help="Keep records describing retired things as current out of the index, or restore them",
    )
    forget.add_argument(
        "--restore",
        metavar="SELECTOR",
        help="A record id, a rule, or rule:detail (e.g. retired:Holded) to bring back",
    )
    forget.add_argument(
        "--echoes",
        action="store_true",
        help="Select synthesis records written about a lone harness echo instead",
    )
    forget.add_argument(
        "--apply", action="store_true", help="Write the ledger; otherwise only report"
    )
