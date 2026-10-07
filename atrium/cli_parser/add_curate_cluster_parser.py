"""Register the `curate-cluster` subcommand on the atrium parser."""

from atrium.cli_parser.sub_parsers import SubParsers


def add_curate_cluster_parser(subcommands: SubParsers) -> None:
    """Register `curate-cluster` and its flags."""
    cluster = subcommands.add_parser(
        "curate-cluster",
        help="Adjudicate the near pairs of the claim ledger into clusters and contradictions",
    )
    cluster.add_argument("--threshold", type=float, default=0.75, help="Cosine floor for a pair")
    cluster.add_argument("--neighbours", type=int, default=5, help="Neighbours kept per claim")
    cluster.add_argument("--budget", type=int, default=1000, help="Maximum pairs adjudicated")
    cluster.add_argument("--model", default=None, help="Ollama model to adjudicate with")
