"""Atrium command line — the core surface every adapter wraps."""

import argparse
import sys
from pathlib import Path

from atrium.commands.positive_limit import positive_limit
from atrium.commands.run_doctor import run_doctor
from atrium.commands.run_embed import run_embed
from atrium.commands.run_ingest import run_ingest
from atrium.commands.run_ingest_notes import run_ingest_notes
from atrium.commands.run_ingest_synthesis import run_ingest_synthesis
from atrium.commands.run_recall import run_recall
from atrium.commands.run_rekey_synthesis import run_rekey_synthesis
from atrium.commands.run_search import run_search
from atrium.commands.run_status import run_status
from atrium.commands.run_synthesize import run_synthesize
from atrium.session.record_session_contract import RECORD_SESSION_CONTRACT
from atrium.state.archive_path import archive_path
from atrium.state.record_refresh import record_refresh
from atrium.state.state_directory import state_directory
from atrium.synthesize.default_registry import default_registry


def main(argv: list[str] | None = None) -> int:  # noqa: PLR0911, PLR0912, PLR0915 -- one flat parser and one return per subcommand; a dispatch table would hide the arg wiring this makes greppable
    """Parse one subcommand and run it; the adapters wrap this, never each other."""
    parser = argparse.ArgumentParser(prog="atrium", description=__doc__)
    # Resolved here, not at import: the instance is chosen by the environment
    # and the working directory of this invocation, and the archive of an
    # instance sits beside its config, never under the home directory.
    state = state_directory()
    refresh_stamp = state / "last-refresh"
    archive = archive_path()
    parser.add_argument("--index", type=Path, default=state / "index.sqlite3")
    subcommands = parser.add_subparsers(dest="command", required=True)

    ingest = subcommands.add_parser("ingest", help="Index a canonical archive")
    ingest.add_argument("archive", type=Path)
    ingest.add_argument(
        "--partial",
        action="store_true",
        help="The archive is a slice, not a source's full export: skip the sweep "
        "that removes conversations absent from it",
    )

    notes = subcommands.add_parser("ingest-notes", help="Index a tree of curated markdown notes")
    notes.add_argument("root", type=Path)
    notes.add_argument("--provider", default="brain")
    notes.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="DIR",
        help="Directory name to skip anywhere under the root (repeatable)",
    )
    notes.add_argument(
        "--partial",
        action="store_true",
        help="The root is a slice of the provider's notes: skip the sweep that "
        "removes notes absent from it",
    )
    notes.add_argument(
        "--third-party",
        action="store_true",
        help="The tree is saved third-party content, not the user's own words: "
        "records are marked role 'source', stay lexically searchable, and are "
        "never embedded or injected at session start",
    )

    subcommands.add_parser("embed", help="Embed semantic-layer records that lack a vector")

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

    subcommands.add_parser("ingest-synthesis", help="Index every synthesis record in the registry")
    subcommands.add_parser(
        "curate-screen",
        help="Screen the synthesis registry into a deterministic claim candidate ledger",
    )
    extract = subcommands.add_parser(
        "curate-extract",
        help="Structure a stratified sample of the claim candidate ledger with the local model",
    )
    extract.add_argument("--size", type=int, default=500, help="Working sample size")
    extract.add_argument("--holdout", type=int, default=100, help="Held-out sample size")
    extract.add_argument("--model", default=None, help="Ollama model to extract with")

    cluster = subcommands.add_parser(
        "curate-cluster",
        help="Adjudicate the near pairs of the claim ledger into clusters and contradictions",
    )
    cluster.add_argument("--threshold", type=float, default=0.75, help="Cosine floor for a pair")
    cluster.add_argument("--neighbours", type=int, default=5, help="Neighbours kept per claim")
    cluster.add_argument("--budget", type=int, default=1000, help="Maximum pairs adjudicated")
    cluster.add_argument("--model", default=None, help="Ollama model to adjudicate with")

    neighbours = subcommands.add_parser(
        "curate-neighbours",
        help="Embed the whole candidate ledger and count its near-duplicate pairs",
    )
    neighbours.add_argument("--threshold", type=float, default=0.80, help="Cosine floor")
    neighbours.add_argument("--neighbours", type=int, default=5, help="Neighbours per candidate")

    publishable = subcommands.add_parser(
        "curate-publishable",
        help="Classify each claim as durable knowledge, incident evidence or session mechanics",
    )
    publishable.add_argument("--budget", type=int, default=1000, help="Maximum claims judged")
    publishable.add_argument("--model", default=None, help="Ollama model to judge with")

    propose = subcommands.add_parser(
        "curate-propose",
        help="Place each durable claim on a curated page and write proposals for review",
    )
    propose.add_argument("--budget", type=int, default=1000, help="Maximum claims placed")
    propose.add_argument("--model", default=None, help="Ollama model to place with")

    subcommands.add_parser(
        "session-stop",
        help="Claude Code Stop hook decision: refuse the stop when the session owes a record",
    )
    record_session = subcommands.add_parser(
        "record-session",
        help="Write the running session's own synthesis for a frozen checkpoint",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=RECORD_SESSION_CONTRACT,
    )
    record_session.add_argument("--checkpoint", required=True, metavar="ID")
    record_session.add_argument(
        "--nothing-durable",
        action="store_true",
        help="Consume the checkpoint without a record: the interval produced nothing to keep",
    )

    doctor = subcommands.add_parser(
        "doctor", help="Check whether the memory would answer from a world that still exists"
    )
    doctor.add_argument("--archive", type=Path, default=archive)
    doctor.add_argument(
        "--json",
        action="store_true",
        help="Print checks as JSON (name, ok, severity, fixed code) instead of prose",
    )
    doctor.add_argument(
        "--publish",
        action="store_true",
        help="Also publish status/doctor.json atomically. Only the refresh job passes "
        "this, at its end: the run costs minutes, too slow for a reader to poll",
    )

    rekey = subcommands.add_parser(
        "rekey-synthesis",
        help="Re-key the synthesis registry onto the schema 2 event id rule",
    )
    rekey.add_argument("--apply", action="store_true", help="Write; otherwise only report the plan")
    rekey.add_argument(
        "--repair",
        action="store_true",
        help="Ask the archive which rule each record's ids follow, rather than trusting its stamp",
    )
    rekey.add_argument("--archive", type=Path, default=archive)

    search = subcommands.add_parser("search", help="Search the index")
    search.add_argument("query")
    search.add_argument("--limit", type=positive_limit, default=10)
    search.add_argument(
        "--project",
        type=Path,
        default=None,
        metavar="DIR",
        help="Restrict the search to the project containing DIR",
    )
    lanes = search.add_mutually_exclusive_group()
    lanes.add_argument(
        "--substring",
        action="store_true",
        help="Match fragments inside words instead of whole words",
    )
    lanes.add_argument("--words", action="store_true", help="Lexical lane only, no fusion")
    lanes.add_argument("--dense", action="store_true", help="Semantic lane only, no fusion")

    prepare = subcommands.add_parser("prepare-context", help="Add derived context lookup indexes")
    prepare.add_argument("--json", action="store_true", help="Emit preparation metadata as JSON")

    context = subcommands.add_parser("context", help="Retrieve bounded project and curated context")
    context.add_argument("query")
    context.add_argument("--project", type=Path, default=None)
    context.add_argument("--limit", type=positive_limit, default=8)
    context.add_argument("--max-chars", type=positive_limit, default=16000)
    context.add_argument("--lane", choices=("auto", "words", "substring", "dense"), default="auto")
    context.add_argument(
        "--json", action="store_true", help="Emit the shared JSON contract (default)"
    )

    recall = subcommands.add_parser(
        "recall", help="Render this project's session-start recall block"
    )
    recall.add_argument(
        "--cwd",
        type=Path,
        default=Path.cwd(),
        help="Directory whose project to recall (default: the working directory)",
    )
    recall.add_argument("--limit", type=positive_limit, default=12)
    recall.add_argument("--archive", type=Path, default=archive)
    recall.add_argument("--refresh-stamp", type=Path, default=refresh_stamp)

    status = subcommands.add_parser("status", help="Show what the index holds, and how stale")
    status.add_argument("--archive", type=Path, default=archive)
    status.add_argument("--refresh-stamp", type=Path, default=refresh_stamp)
    status.add_argument("--synthesis-registry", type=Path, default=None)
    status.add_argument(
        "--coverage",
        action="store_true",
        help="Also report how many real projects have synthesized memory. Off by "
        "default: it scans every record and costs ~44s, and the answer moves slowly",
    )
    status.add_argument(
        "--publish",
        action="store_true",
        help="Also publish status/refresh.json atomically. Only the refresh job passes "
        "this, at its end, so the file has exactly one writer",
    )
    status.add_argument(
        "--json",
        action="store_true",
        help="Print the same redacted document --publish writes (counts, ages, "
        "populations) instead of the text report",
    )

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

    args = parser.parse_args(argv)
    if args.command == "synthesis":
        from atrium.ledger.run_synthesis_cli import run_synthesis_cli

        return run_synthesis_cli(
            args.view,
            default_registry(),
            limit=min(getattr(args, "limit", 1), 500),
            days=min(getattr(args, "days", 14), 90),
            job_key=getattr(args, "job_key", None),
        )
    if args.command == "ingest":
        ingested = run_ingest(args.index, args.archive, sweep=not args.partial)
        if ingested == 0:
            record_refresh(refresh_stamp)
        return ingested
    if args.command == "ingest-notes":
        ingested = run_ingest_notes(
            args.index,
            args.root,
            args.provider,
            tuple(args.exclude),
            sweep=not args.partial,
            role="source" if args.third_party else "note",
        )
        if ingested == 0:
            record_refresh(refresh_stamp)
        return ingested
    if args.command == "embed":
        return run_embed(args.index)
    if args.command == "synthesize":
        return run_synthesize(
            args.archive,
            args.limit,
            args.dry_run,
            args.producer,
            args.workers,
            args.model,
            args.effort,
            args.project,
            args.workspace,
            include_session_covered=args.include_session_covered,
        )
    if args.command == "ingest-synthesis":
        return run_ingest_synthesis(args.index)
    if args.command == "curate-screen":
        from atrium.curate.run_curate_screen_cli import run_curate_screen_cli

        return run_curate_screen_cli(state_directory() / "synthesis")
    if args.command == "curate-extract":
        from atrium.curate.run_curate_extract_cli import run_curate_extract_cli
        from atrium.synthesize.local_lane_call import LOCAL_DEFAULT_MODEL

        return run_curate_extract_cli(args.size, args.holdout, args.model or LOCAL_DEFAULT_MODEL)
    if args.command == "curate-cluster":
        from atrium.curate.run_curate_cluster_cli import run_curate_cluster_cli
        from atrium.synthesize.local_lane_call import LOCAL_DEFAULT_MODEL

        return run_curate_cluster_cli(
            args.threshold, args.neighbours, args.budget, args.model or LOCAL_DEFAULT_MODEL
        )
    if args.command == "curate-neighbours":
        from atrium.curate.run_curate_neighbours_cli import run_curate_neighbours_cli

        return run_curate_neighbours_cli(args.threshold, args.neighbours)
    if args.command == "curate-publishable":
        from atrium.curate.run_curate_publishable_cli import run_curate_publishable_cli
        from atrium.synthesize.local_lane_call import LOCAL_DEFAULT_MODEL

        return run_curate_publishable_cli(args.budget, args.model or LOCAL_DEFAULT_MODEL)
    if args.command == "curate-propose":
        from atrium.curate.run_curate_propose_cli import run_curate_propose_cli
        from atrium.synthesize.local_lane_call import LOCAL_DEFAULT_MODEL

        return run_curate_propose_cli(args.budget, args.model or LOCAL_DEFAULT_MODEL)
    if args.command == "session-stop":
        from atrium.session.run_session_stop_cli import run_session_stop_cli

        return run_session_stop_cli()
    if args.command == "record-session":
        from atrium.session.run_record_session_cli import run_record_session_cli

        return run_record_session_cli(
            args.checkpoint, default_registry(), nothing_durable=args.nothing_durable
        )
    if args.command == "rekey-synthesis":
        return run_rekey_synthesis(apply=args.apply, repair=args.repair, archive=args.archive)
    if args.command == "doctor":
        return run_doctor(
            args.index, args.archive, refresh_stamp, as_json=args.json, publish=args.publish
        )
    if args.command == "search":
        lane = (
            "substring"
            if args.substring
            else "words"
            if args.words
            else "dense"
            if args.dense
            else "auto"
        )
        return run_search(args.index, args.query, args.limit, lane, args.project)
    if args.command == "prepare-context":
        from atrium.context.prepare_context_cli import prepare_context_cli

        return prepare_context_cli(args.index)
    if args.command == "context":
        from atrium.context.run_context_cli import run_context_cli

        try:
            return run_context_cli(
                args.index, args.query, args.project, args.limit, args.max_chars, args.lane, state
            )
        except ValueError as error:
            parser.error(str(error))
    if args.command == "recall":
        return run_recall(args.index, args.cwd, args.limit, args.archive, args.refresh_stamp)
    return run_status(
        args.index,
        args.archive,
        args.refresh_stamp,
        args.synthesis_registry,
        coverage=args.coverage,
        publish=state if args.publish else None,
        as_json=args.json,
    )


if __name__ == "__main__":
    sys.exit(main())
