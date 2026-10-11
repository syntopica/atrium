"""Register the `erase` subcommand on the atrium parser."""

from pathlib import Path

from atrium.cli_parser.sub_parsers import SubParsers


def add_erase_parser(subcommands: SubParsers) -> None:
    """Register `erase` and its flags.

    No ``--archive``: the generation check must read the archive the next
    ingest will read, so it is always the configured one.
    """
    erase = subcommands.add_parser(
        "erase",
        help="Remove what was derived from the conversations an applied scribe erasure plan erased",
    )
    erase.add_argument("--plan", type=Path, required=True, help="The applied erasure plan JSON")
    erase.add_argument("--apply", action="store_true", help="Delete; otherwise only report")
