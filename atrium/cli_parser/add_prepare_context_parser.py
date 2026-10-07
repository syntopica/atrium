"""Register the `prepare-context` subcommand on the atrium parser."""

from atrium.cli_parser.sub_parsers import SubParsers


def add_prepare_context_parser(subcommands: SubParsers) -> None:
    """Register `prepare-context` and its flags."""
    prepare = subcommands.add_parser("prepare-context", help="Add derived context lookup indexes")
    prepare.add_argument("--json", action="store_true", help="Emit preparation metadata as JSON")
