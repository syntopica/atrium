"""Register the `parity` subcommand on the atrium parser."""

from pathlib import Path

from atrium.cli_parser.sub_parsers import SubParsers


def add_parity_parser(subcommands: SubParsers) -> None:
    """Register `parity` and its argument."""
    parity = subcommands.add_parser(
        "parity",
        help="Compare an index rebuilt from a materialized export with --index, read-only",
    )
    parity.add_argument("test", type=Path, help="The rebuilt test index")
