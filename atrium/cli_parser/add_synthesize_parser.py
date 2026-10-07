"""Register the `synthesize` subcommand on the atrium parser."""

from pathlib import Path

from atrium.cli_parser.sub_parsers import SubParsers
from atrium.commands.positive_limit import positive_limit


def add_synthesize_parser(subcommands: SubParsers) -> None:
    """Register `synthesize` and its flags."""
    synthesize = subcommands.add_parser(
        "synthesize", help="Synthesize archive episodes into the registry (Max lane)"
    )
    synthesize.add_argument("archive", type=Path)
    synthesize.add_argument("--limit", type=positive_limit, default=None)
    synthesize.add_argument("--dry-run", action="store_true")
    synthesize.add_argument(
        "--producer",
        choices=("agy", "codex", "local", "max", "task"),
        default="agy",
        help="agy: Gemini bulk quota via the Antigravity CLI (default -- the "
        "standing routing rule for whole-corpus passes); codex: the Codex "
        "CLI's quota; local: a model served by Ollama on this machine, off every "
        "quota; max: the Claude Max OAuth lane; task: agy through the worker's "
        "atrium.tasks queue, --model names the worker profile",
    )
    synthesize.add_argument("--workers", type=positive_limit, default=3)
    synthesize.add_argument(
        "--model",
        default=None,
        help="Codex, agy and local lanes: pin the model instead of the lane default. "
        "It enters the job key, so a different model is a different population",
    )
    synthesize.add_argument(
        "--effort",
        default=None,
        choices=("low", "medium", "high", "xhigh"),
        help="Codex lane only: reasoning effort. Synthesis is extraction, not "
        "judgement, so the account default is usually the wrong price",
    )
    scope = synthesize.add_mutually_exclusive_group()
    scope.add_argument(
        "--project",
        type=Path,
        default=None,
        metavar="DIR",
        help="Synthesize only the project containing DIR. Whole-corpus coverage "
        "costs about a dozen weekly quota cycles; the projects actually missing "
        "memory are a handful, and `status --coverage` names them",
    )
    scope.add_argument(
        "--workspace",
        default=None,
        metavar="PREFIX",
        help="Same, by stored workspace (e.g. '[HOME]/p/project-before'). The one that "
        "works for a project no longer on disk -- which is precisely the memory "
        "nothing else can reconstruct",
    )

    synthesize.add_argument(
        "--include-session-covered",
        action="store_true",
        help="Also synthesize conversations the session producer already recorded "
        "(skipped by default: the author's record is there, paying a cold reader "
        "for the same conversation is the one thing the registry exists to avoid)",
    )
