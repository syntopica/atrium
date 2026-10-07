"""Register the `curate-extract` subcommand on the atrium parser."""

from atrium.cli_parser.sub_parsers import SubParsers


def add_curate_extract_parser(subcommands: SubParsers) -> None:
    """Register `curate-extract` and its flags."""
    extract = subcommands.add_parser(
        "curate-extract",
        help="Structure a stratified sample of the claim candidate ledger with the local model",
    )
    extract.add_argument("--size", type=int, default=500, help="Working sample size")
    extract.add_argument("--holdout", type=int, default=100, help="Held-out sample size")
    extract.add_argument("--model", default=None, help="Ollama model to extract with")
