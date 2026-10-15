"""Write one statement an agent chose to keep, and index it at once."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from atrium.ledger.read_record_file import read_record_file
from atrium.remember.build_remembered_record import build_remembered_record
from atrium.remember.index_remembered_record import index_remembered_record
from atrium.remember.missing_supersede_targets import missing_supersede_targets
from atrium.remember.remember_payload import remember_payload
from atrium.store.open_store import open_store
from atrium.synthesize.has_record import has_record
from atrium.synthesize.write_record import write_record

if TYPE_CHECKING:
    from atrium.context.context_embedder import ContextEmbedder


def remember(  # noqa: PLR0913 -- one statement, its scope, its targets and where it goes
    payload: Any,
    workspace: str,
    *,
    supersedes: list[str],
    registry: Path,
    index: Path,
    embedder: "ContextEmbedder | None",
) -> dict[str, Any]:
    """Return the receipt: record id, whether it existed, and whether it is searchable yet.

    The registry write is the durable act and happens first; the index write
    is a convenience that the next refresh would do anyway. A target that is
    not a synthesized episode in the index is refused before anything is
    written, because a supersession pointing at nothing marks nothing and
    tells the agent it corrected a record it did not.
    """
    output = remember_payload(payload)
    connection = open_store(index)
    try:
        missing = missing_supersede_targets(connection, supersedes)
        if missing:
            raise ValueError(f"not a synthesized episode in the index: {', '.join(missing)}")
        authored_at = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        record = build_remembered_record(output, workspace, supersedes, authored_at)
        existed = has_record(registry, record["job_key"])
        # A repeat names the same key; the stored copy, with its first date,
        # is what the next ingest indexes, so it is what gets indexed now.
        stored = read_record_file(write_record(registry, record["job_key"], record))
        record = stored if stored is not None else record
        try:
            record_id = index_remembered_record(connection, record, embedder)
            searchable = True
        except sqlite3.OperationalError as error:
            if "locked" not in str(error):
                raise
            record_id, searchable = None, False
    finally:
        connection.close()
    return {
        "record_id": record_id,
        "job_key": record["job_key"],
        "existed": existed,
        "workspace": workspace,
        "supersedes": record["supersedes"],
        "searchable_now": searchable,
    }
