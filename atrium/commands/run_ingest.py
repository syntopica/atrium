"""The `ingest` handler of the atrium CLI."""

from pathlib import Path

from atrium.ingest.admission_tally import AdmissionTally
from atrium.ingest.read_archive import read_archive
from atrium.ingest.to_records import to_records
from atrium.ingest.workspace_aliases import workspace_aliases
from atrium.store.delete_absent_conversations import delete_absent_conversations
from atrium.store.open_store import open_store
from atrium.store.write_conversation import UNCHANGED, write_conversation


def run_ingest(index: Path, archive: Path, *, sweep: bool = True) -> int:
    """Index an archive, or change nothing at all.

    One transaction for the whole run. A malformed line partway through an
    archive must not leave the index holding half a revision: the previous
    behaviour committed each conversation as it went, so a mid-file failure left
    records written but unsearchable, and the operator saw an error next to an
    index that looked populated.

    An archive is a source's full export, so after ingesting it the index must
    hold exactly its conversations for the providers it carries: conversations
    deleted or redacted away upstream never appear in the new input, and only
    the sweep removes them. `--partial` opts out for deliberate slices.
    """
    connection = open_store(index)
    total = 0
    conversations = 0
    unchanged = 0
    removed = 0
    tally = AdmissionTally()
    # Read once per pass, not once per conversation: it is a file on disk and
    # this loop runs 30,000 times.
    aliases = workspace_aliases()
    seen_by_provider: dict[str, set[str]] = {}
    try:
        with connection:
            for conversation in read_archive(archive):
                conversations += 1
                written = write_conversation(
                    connection, conversation["id"], to_records(conversation, tally, aliases)
                )
                unchanged += written == UNCHANGED
                total += max(written, 0)
                provider = conversation.get("source") or "unknown"
                seen_by_provider.setdefault(provider, set()).add(conversation["id"])
            if sweep:
                for provider, seen in seen_by_provider.items():
                    removed += delete_absent_conversations(connection, provider, seen)
    finally:
        connection.close()
    swept = f", {removed} absent removed" if removed else ""
    skipped = f", {unchanged} conversations unchanged" if unchanged else ""
    print(f"  {conversations} conversations -> {total} records written at {index}{skipped}{swept}")
    for label, counts in (("admitted", tally.admitted), ("rejected", tally.rejected)):
        if counts:
            ranked = sorted(counts.items(), key=lambda item: -item[1])
            print(f"  {label}: " + ", ".join(f"{count:,} {name}" for name, count in ranked))
    return 0
