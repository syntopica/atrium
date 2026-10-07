"""Register the `context` subcommand on the atrium parser."""

from pathlib import Path

from atrium.cli_parser.sub_parsers import SubParsers
from atrium.commands.positive_limit import positive_limit


def add_context_parser(subcommands: SubParsers) -> None:
    """Register `context` and its flags."""
    context = subcommands.add_parser("context", help="Retrieve bounded project and curated context")
    context.add_argument("query")
    context.add_argument("--project", type=Path, default=None)
    context.add_argument("--limit", type=positive_limit, default=8)
    context.add_argument("--max-chars", type=positive_limit, default=16000)
    context.add_argument("--lane", choices=("auto", "words", "substring", "dense"), default="auto")
    context.add_argument(
        "--json", action="store_true", help="Emit the shared JSON contract (default)"
    )
