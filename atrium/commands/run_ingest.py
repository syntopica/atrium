"""The `ingest` handler of the atrium CLI."""

from pathlib import Path

from atrium.forget.forget_ledger_file import forget_ledger_file
from atrium.forget.forgotten_ids import forgotten_ids
from atrium.ingest.admission_tally import AdmissionTally
from atrium.ingest.canonical_workspace import canonical_workspace
from atrium.ingest.is_excluded_automation import is_excluded_automation
from atrium.ingest.read_archive import read_archive
from atrium.ingest.read_archive_manifest import read_archive_manifest
from atrium.ingest.rows_sha256 import rows_sha256
from atrium.ingest.to_records import to_records
from atrium.ingest.workspace_aliases import workspace_aliases
from atrium.store.delete_absent_conversations import delete_absent_conversations
from atrium.store.delete_absent_revisions import delete_absent_revisions
from atrium.store.mark_revision_backfill import mark_revision_backfill
from atrium.store.open_store import open_store
from atrium.store.read_revisions import read_revisions
from atrium.store.revision import Revision
from atrium.store.upsert_revision import upsert_revision
from atrium.store.write_archive_generation import write_archive_generation
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

    A conversation whose derived rows hash to the revision stored for it is
    skipped before its stored text is read back. That read was most of the
    stage: on 2026-10-10 a refresh spent 3.6 minutes comparing 54,026
    conversations to write the rows of 6. Automation the pipeline produced
    itself (``is_excluded_automation``) reconciles to no rows, and its verdict is
    kept so the synthesis ingest can drop what was synthesized from it.
    """
    connection = open_store(index)
    total = 0
    conversations = 0
    unchanged = 0
    excluded = 0
    removed = 0
    tally = AdmissionTally()
    # Read once per pass, not once per conversation: it is a file on disk and
    # this loop runs 30,000 times.
    aliases = workspace_aliases()
    forgotten = forgotten_ids(forget_ledger_file())
    seen_by_provider: dict[str, set[str]] = {}
    revisions_by_provider: dict[str, dict[str, Revision]] = {}
    try:
        with connection:
            for conversation in read_archive(archive):
                conversations += 1
                conversation_id = conversation["id"]
                provider = conversation.get("source") or "unknown"
                seen_by_provider.setdefault(provider, set()).add(conversation_id)
                if provider not in revisions_by_provider:
                    revisions_by_provider[provider] = read_revisions(connection, provider)
                automation = is_excluded_automation(provider, conversation.get("workspace"))
                records = (
                    [] if automation else list(to_records(conversation, tally, aliases, forgotten))
                )
                excluded += automation
                revision = Revision(
                    rows_sha256=rows_sha256(records),
                    canonical_workspace=canonical_workspace(
                        conversation.get("workspace"),
                        aliases=aliases,
                        started_at=conversation.get("startedAt"),
                    ),
                    disposition="excluded_automation"
                    if automation
                    else ("indexed" if records else "empty"),
                )
                if revisions_by_provider[provider].get(conversation_id) == revision:
                    unchanged += 1
                    continue
                written = write_conversation(connection, conversation_id, records)
                upsert_revision(connection, conversation_id, provider, revision)
                # Rows and revisions are keyed by conversation id alone: once one
                # provider has written it, no other provider's cached revision
                # may vouch for those rows.
                for cached in revisions_by_provider.values():
                    cached.pop(conversation_id, None)
                revisions_by_provider[provider][conversation_id] = revision
                unchanged += written == UNCHANGED
                total += max(written, 0)
            if sweep:
                for provider, seen in seen_by_provider.items():
                    removed += delete_absent_conversations(connection, provider, seen)
                    delete_absent_revisions(connection, provider, seen)
                mark_revision_backfill(connection)
                # Only a full ingest speaks for a generation: a slice covers a subset.
                write_archive_generation(
                    connection, read_archive_manifest(archive).get("generationId")
                )
    finally:
        connection.close()
    swept = f", {removed} absent removed" if removed else ""
    skipped = f", {unchanged} conversations unchanged" if unchanged else ""
    automation_note = f", {excluded} automation excluded" if excluded else ""
    print(
        f"  {conversations} conversations -> {total} records written at {index}"
        f"{skipped}{automation_note}{swept}"
    )
    for label, counts in (("admitted", tally.admitted), ("rejected", tally.rejected)):
        if counts:
            ranked = sorted(counts.items(), key=lambda item: -item[1])
            print(f"  {label}: " + ", ".join(f"{count:,} {name}" for name, count in ranked))
    return 0
