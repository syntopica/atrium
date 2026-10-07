"""Atrium command line — the core surface every adapter wraps."""

import sys

from atrium.cli_parser.build_parser import build_parser
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
from atrium.state.archive_path import archive_path
from atrium.state.record_refresh import record_refresh
from atrium.state.state_directory import state_directory
from atrium.synthesize.default_registry import default_registry


def main(argv: list[str] | None = None) -> int:  # noqa: PLR0911, PLR0912, PLR0915 -- one return per subcommand; a dispatch table would hide the arg wiring this makes greppable, and the parser it dispatches on stays flat in cli_parser/build_parser.py
    """Parse one subcommand and run it; the adapters wrap this, never each other."""
    # Resolved here, not at import: the instance is chosen by the environment
    # and the working directory of this invocation, and the archive of an
    # instance sits beside its config, never under the home directory.
    state = state_directory()
    refresh_stamp = state / "last-refresh"
    archive = archive_path()
    parser = build_parser(state, archive, refresh_stamp, __doc__)
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
