"""The `ingest-synthesis` handler of the atrium CLI."""

from pathlib import Path

from atrium.record import Record
from atrium.store.delete_absent_conversations import delete_absent_conversations
from atrium.store.delete_absent_revisions import delete_absent_revisions
from atrium.store.open_store import open_store
from atrium.store.read_revisions import read_revisions
from atrium.store.read_source_revisions import read_source_revisions
from atrium.store.revision import Revision
from atrium.store.revisions_backfilled import revisions_backfilled
from atrium.store.upsert_revision import upsert_revision
from atrium.store.write_conversation import UNCHANGED, write_conversation
from atrium.synthesize.default_registry import default_registry


def run_ingest_synthesis(index: Path) -> int:
    """Index one record per episode; same sweep contract as the other ingests.

    Several recipe populations may hold the same episode (different producers,
    different job keys). The active-recipe manifest picks which one the index
    serves, so coexistence in the registry never becomes a duplicate -- or a
    primary-key collision -- in the index.

    The source conversation's workspace and verdict come from the raw ingest's
    revisions: registry records store no workspace, and an excluded source has no
    raw rows left to recover one from, so only the revision still says that its
    synthesis must not be served. An index whose revisions were never filled
    falls back to reading workspaces from the raw rows, as before.
    """
    from atrium.ingest.canonical_workspace import canonical_workspace
    from atrium.ingest.conversation_workspaces import conversation_workspaces
    from atrium.ingest.rows_sha256 import rows_sha256
    from atrium.ingest.to_synthesis_records import to_synthesis_records
    from atrium.synthesize.active_recipe_priority import active_recipe_priority
    from atrium.synthesize.choose_served_records import choose_served_records
    from atrium.synthesize.read_records import read_records

    chosen = choose_served_records(
        read_records(default_registry()), active_recipe_priority(default_registry())
    )

    connection = open_store(index)
    total = 0
    unchanged = 0
    excluded = 0
    seen: set[str] = set()
    try:
        # Read before writing anything: both maps come from the raw ingest,
        # which this pass never touches.
        # A verdict counts even before the backfill: a purge writes them first,
        # and the raw rows it removed are no longer there to say otherwise.
        sources = read_source_revisions(connection)
        automation = {
            conversation_id
            for conversation_id, revision in sources.items()
            if revision.disposition == "excluded_automation"
        }
        # A revision with no workspace is an answer, not a gap: the archived
        # conversation has none, and a registry value must not replace it.
        workspaces: dict[str, str | None] = (
            {
                conversation_id: revision.canonical_workspace
                for conversation_id, revision in sources.items()
            }
            if revisions_backfilled(connection)
            else dict(conversation_workspaces(connection))
        )
        stored = read_revisions(connection, "synthesis")
        by_conversation: dict[str, list[Record]] = {}
        workspace_of: dict[str, str | None] = {}
        for record in chosen.values():
            if record["conversation_id"] in automation:
                excluded += 1
                continue
            # A session record names its own project: its conversation is
            # not archived yet, so the archive's map cannot know it.
            workspace = (
                workspaces[record["conversation_id"]]
                if record["conversation_id"] in workspaces
                else canonical_workspace(record.get("workspace"))
            )
            for row in to_synthesis_records(record, workspace):
                by_conversation.setdefault(row.conversation_id, []).append(row)
                workspace_of[row.conversation_id] = workspace
        with connection:
            for conversation_id, rows in sorted(by_conversation.items()):
                seen.add(conversation_id)
                revision = Revision(rows_sha256(rows), workspace_of[conversation_id], "indexed")
                if stored.get(conversation_id) == revision:
                    unchanged += 1
                    continue
                written = write_conversation(connection, conversation_id, rows)
                upsert_revision(connection, conversation_id, "synthesis", revision)
                unchanged += written == UNCHANGED
                total += max(written, 0)
            removed = delete_absent_conversations(connection, "synthesis", seen)
            delete_absent_revisions(connection, "synthesis", seen)
    finally:
        connection.close()
    swept = f", {removed} absent removed" if removed else ""
    skipped = f", {unchanged} unchanged" if unchanged else ""
    automation_note = f", {excluded} episodes of automation excluded" if excluded else ""
    print(
        f"  {len(seen)} conversations -> {total} synthesis records written"
        f"{skipped}{automation_note}{swept}"
    )
    return 0
