"""Run one parsed atrium subcommand; the CLI's dispatch table."""

from argparse import ArgumentParser, Namespace
from pathlib import Path

from atrium.commands.run_curate_command import run_curate_command
from atrium.commands.run_doctor import run_doctor
from atrium.commands.run_embed import run_embed
from atrium.commands.run_erase import run_erase
from atrium.commands.run_forget import run_forget
from atrium.commands.run_ingest import run_ingest
from atrium.commands.run_ingest_notes import run_ingest_notes
from atrium.commands.run_ingest_synthesis import run_ingest_synthesis
from atrium.commands.run_recall import run_recall
from atrium.commands.run_rekey_synthesis import run_rekey_synthesis
from atrium.commands.run_repair_index import run_repair_index
from atrium.commands.run_search import run_search
from atrium.commands.run_status import run_status
from atrium.commands.run_synthesize import run_synthesize
from atrium.commands.search_lane import search_lane
from atrium.state.record_refresh import record_refresh
from atrium.synthesize.default_registry import default_registry
from atrium.telemetry.append_lane_event import append_lane_event
from atrium.telemetry.run_lane_status import run_lane_status


def run_command(  # noqa: PLR0911, PLR0912 -- one return per subcommand; a dispatch table would hide the arg wiring this makes greppable, and the parser it dispatches on stays flat in cli_parser/build_parser.py
    args: Namespace, parser: ArgumentParser, state: Path, refresh_stamp: Path, archive: Path
) -> int:
    """Run the subcommand ``args`` names; the adapters wrap this, never each other."""
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
    if args.command.startswith("curate-"):
        return run_curate_command(args)
    if args.command == "session-stop":
        from atrium.session.run_session_stop_cli import run_session_stop_cli

        return run_session_stop_cli()
    if args.command == "record-session":
        from atrium.session.run_record_session_cli import run_record_session_cli

        return run_record_session_cli(
            args.checkpoint, default_registry(), state, nothing_durable=args.nothing_durable
        )
    if args.command == "remember":
        from atrium.remember.run_remember_cli import run_remember_cli

        append_lane_event(state, "cli.remember", "write")
        return run_remember_cli(args.index, default_registry(), args.project, args.supersedes)
    if args.command == "erase":
        return run_erase(args.index, args.plan, archive, apply=args.apply)
    if args.command == "repair-index":
        return run_repair_index(args.index, state, apply=args.apply)
    if args.command == "forget":
        return run_forget(args.index, state, restore=args.restore, apply=args.apply)
    if args.command == "rekey-synthesis":
        return run_rekey_synthesis(apply=args.apply, repair=args.repair, archive=args.archive)
    if args.command == "doctor":
        return run_doctor(
            args.index, args.archive, refresh_stamp, as_json=args.json, publish=args.publish
        )
    if args.command == "search":
        lane = search_lane(args)
        append_lane_event(state, "cli.search", lane)
        return run_search(args.index, args.query, args.limit, lane, args.project)
    if args.command == "prepare-context":
        from atrium.context.prepare_context_cli import prepare_context_cli

        return prepare_context_cli(args.index)
    if args.command == "context":
        from atrium.context.run_context_cli import run_context_cli

        try:
            append_lane_event(state, "cli.context", args.lane)
            return run_context_cli(
                args.index, args.query, args.project, args.limit, args.max_chars, args.lane, state
            )
        except ValueError as error:
            parser.error(str(error))
    if args.command == "serve-context":
        from atrium.serve.serve_context import serve_context

        return serve_context(args.index, state, args.interval)
    if args.command == "file-context":
        from atrium.recall.run_file_context_cli import run_file_context_cli

        append_lane_event(state, "cli.file_context", "words")
        return run_file_context_cli(args.index, args.path, args.limit)
    if args.command == "recall":
        append_lane_event(state, "cli.recall", "recent")
        return run_recall(args.index, args.cwd, args.limit, args.archive, args.refresh_stamp)
    if args.lanes:
        if not 1 <= args.days <= 365:  # noqa: PLR2004 -- documented retention window
            parser.error("--days must be between 1 and 365")
        return run_lane_status(state, args.days, args.json)
    return run_status(
        args.index,
        args.archive,
        args.refresh_stamp,
        args.synthesis_registry,
        coverage=args.coverage,
        publish=state if args.publish else None,
        as_json=args.json,
    )
