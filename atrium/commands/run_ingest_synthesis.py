"""The `ingest-synthesis` handler of the atrium CLI."""

from pathlib import Path

from atrium.record import Record
from atrium.store.delete_absent_conversations import delete_absent_conversations
from atrium.store.open_store import open_store
from atrium.store.write_conversation import UNCHANGED, write_conversation
from atrium.synthesize.default_registry import default_registry


def run_ingest_synthesis(index: Path) -> int:
    """Index one record per episode; same sweep contract as the other ingests.

    Several recipe populations may hold the same episode (different producers,
    different job keys). The active-recipe manifest picks which one the index
    serves, so coexistence in the registry never becomes a duplicate -- or a
    primary-key collision -- in the index.
    """
    from atrium.ingest.canonical_workspace import canonical_workspace
    from atrium.ingest.conversation_workspaces import conversation_workspaces
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
    seen: set[str] = set()
    try:
        # Read the workspaces before writing anything: the map comes from the
        # raw conversations, which this pass never touches.
        workspaces = conversation_workspaces(connection)
        by_conversation: dict[str, list[Record]] = {}
        for record in chosen.values():
            # A session record names its own project: its conversation is
            # not archived yet, so the archive's map cannot know it.
            workspace = workspaces.get(record["conversation_id"]) or canonical_workspace(
                record.get("workspace")
            )
            for row in to_synthesis_records(record, workspace):
                by_conversation.setdefault(row.conversation_id, []).append(row)
        with connection:
            for conversation_id, rows in sorted(by_conversation.items()):
                written = write_conversation(connection, conversation_id, rows)
                unchanged += written == UNCHANGED
                total += max(written, 0)
                seen.add(conversation_id)
            removed = delete_absent_conversations(connection, "synthesis", seen)
    finally:
        connection.close()
    swept = f", {removed} absent removed" if removed else ""
    skipped = f", {unchanged} unchanged" if unchanged else ""
    print(f"  {len(seen)} conversations -> {total} synthesis records written{skipped}{swept}")
    return 0
