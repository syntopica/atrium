"""Register the `serve-context` subcommand on the atrium parser."""

from atrium.cli_parser.sub_parsers import SubParsers


def add_serve_context_parser(subcommands: SubParsers) -> None:
    """Register `serve-context` and its flags."""
    serve = subcommands.add_parser(
        "serve-context",
        help="Keep the embedder and the vectors resident and answer `context` over a socket",
    )
    serve.add_argument(
        "--interval",
        type=float,
        default=60.0,
        help="Seconds between checks for new vectors (default 60)",
    )
