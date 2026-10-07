"""Register the `curate-neighbours` subcommand on the atrium parser."""

from atrium.cli_parser.sub_parsers import SubParsers


def add_curate_neighbours_parser(subcommands: SubParsers) -> None:
    """Register `curate-neighbours` and its flags."""
    neighbours = subcommands.add_parser(
        "curate-neighbours",
        help="Embed the whole candidate ledger and count its near-duplicate pairs",
    )
    neighbours.add_argument("--threshold", type=float, default=0.80, help="Cosine floor")
    neighbours.add_argument("--neighbours", type=int, default=5, help="Neighbours per candidate")
