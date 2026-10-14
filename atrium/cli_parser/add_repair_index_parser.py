"""Register the `repair-index` subcommand on the atrium parser."""

from atrium.cli_parser.sub_parsers import SubParsers


def add_repair_index_parser(subcommands: SubParsers) -> None:
    """Register `repair-index` and its flags."""
    repair = subcommands.add_parser(
        "repair-index",
        help="Check the full-text indexes against the records; rebuild an inconsistent one",
    )
    repair.add_argument(
        "--apply", action="store_true", help="Rebuild a failing index; otherwise only check"
    )
