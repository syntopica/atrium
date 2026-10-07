"""Build the atrium parser: one flat registration per subcommand, in help order."""

import argparse
from pathlib import Path

from atrium.cli_parser.add_context_parser import add_context_parser
from atrium.cli_parser.add_curate_cluster_parser import add_curate_cluster_parser
from atrium.cli_parser.add_curate_extract_parser import add_curate_extract_parser
from atrium.cli_parser.add_curate_neighbours_parser import add_curate_neighbours_parser
from atrium.cli_parser.add_curate_propose_parser import add_curate_propose_parser
from atrium.cli_parser.add_curate_publishable_parser import add_curate_publishable_parser
from atrium.cli_parser.add_doctor_parser import add_doctor_parser
from atrium.cli_parser.add_ingest_notes_parser import add_ingest_notes_parser
from atrium.cli_parser.add_ingest_parser import add_ingest_parser
from atrium.cli_parser.add_prepare_context_parser import add_prepare_context_parser
from atrium.cli_parser.add_recall_parser import add_recall_parser
from atrium.cli_parser.add_record_session_parser import add_record_session_parser
from atrium.cli_parser.add_rekey_synthesis_parser import add_rekey_synthesis_parser
from atrium.cli_parser.add_search_parser import add_search_parser
from atrium.cli_parser.add_status_parser import add_status_parser
from atrium.cli_parser.add_synthesis_parser import add_synthesis_parser
from atrium.cli_parser.add_synthesize_parser import add_synthesize_parser


def build_parser(
    state: Path, archive: Path, refresh_stamp: Path, description: str | None
) -> argparse.ArgumentParser:
    """Build the parser every adapter shares; paths are resolved by the caller."""
    parser = argparse.ArgumentParser(prog="atrium", description=description)
    parser.add_argument("--index", type=Path, default=state / "index.sqlite3")
    subcommands = parser.add_subparsers(dest="command", required=True)
    add_ingest_parser(subcommands)
    add_ingest_notes_parser(subcommands)
    subcommands.add_parser("embed", help="Embed semantic-layer records that lack a vector")
    add_synthesize_parser(subcommands)
    subcommands.add_parser("ingest-synthesis", help="Index every synthesis record in the registry")
    subcommands.add_parser(
        "curate-screen",
        help="Screen the synthesis registry into a deterministic claim candidate ledger",
    )
    add_curate_extract_parser(subcommands)
    add_curate_cluster_parser(subcommands)
    add_curate_neighbours_parser(subcommands)
    add_curate_publishable_parser(subcommands)
    add_curate_propose_parser(subcommands)
    subcommands.add_parser(
        "session-stop",
        help="Claude Code Stop hook decision: refuse the stop when the session owes a record",
    )
    add_record_session_parser(subcommands)
    add_doctor_parser(subcommands, archive)
    add_rekey_synthesis_parser(subcommands, archive)
    add_search_parser(subcommands)
    add_prepare_context_parser(subcommands)
    add_context_parser(subcommands)
    add_recall_parser(subcommands, archive, refresh_stamp)
    add_status_parser(subcommands, archive, refresh_stamp)
    add_synthesis_parser(subcommands)
    return parser
