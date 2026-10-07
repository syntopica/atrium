"""Register the `synthesis` subcommand on the atrium parser."""

from atrium.cli_parser.sub_parsers import SubParsers
from atrium.commands.positive_limit import positive_limit


def add_synthesis_parser(subcommands: SubParsers) -> None:
    """Register `synthesis` and its flags."""
    synthesis = subcommands.add_parser(
        "synthesis", help="Read what synthesis did: newest records, tokens, passes"
    )
    views = synthesis.add_subparsers(dest="view", required=True)
    recent = views.add_parser(
        "recent", help="Newest records with model, tokens and counts; tokens per day"
    )
    recent.add_argument("--limit", type=positive_limit, default=50)
    recent.add_argument("--days", type=positive_limit, default=14)
    passes = views.add_parser("passes", help="Recent passes from the wrapper's tick log")
    passes.add_argument("--limit", type=positive_limit, default=20)
    show = views.add_parser("show", help="One record with its synthesized content")
    show.add_argument("--job-key", required=True)
    for view in (recent, passes, show):
        view.add_argument("--json", action="store_true", help="JSON output (the only format)")
