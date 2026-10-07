"""Register the `curate-propose` subcommand on the atrium parser."""

from atrium.cli_parser.sub_parsers import SubParsers


def add_curate_propose_parser(subcommands: SubParsers) -> None:
    """Register `curate-propose` and its flags."""
    propose = subcommands.add_parser(
        "curate-propose",
        help="Place each durable claim on a curated page and write proposals for review",
    )
    propose.add_argument("--budget", type=int, default=1000, help="Maximum claims placed")
    propose.add_argument("--model", default=None, help="Ollama model to place with")
