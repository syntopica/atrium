"""Register the `curate-publishable` subcommand on the atrium parser."""

from atrium.cli_parser.sub_parsers import SubParsers


def add_curate_publishable_parser(subcommands: SubParsers) -> None:
    """Register `curate-publishable` and its flags."""
    publishable = subcommands.add_parser(
        "curate-publishable",
        help="Classify each claim as durable knowledge, incident evidence or session mechanics",
    )
    publishable.add_argument("--budget", type=int, default=1000, help="Maximum claims judged")
    publishable.add_argument("--model", default=None, help="Ollama model to judge with")
