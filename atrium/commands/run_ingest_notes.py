"""The `ingest-notes` handler of the atrium CLI."""

from pathlib import Path

from atrium.ingest.admission_tally import AdmissionTally
from atrium.ingest.read_notes import read_notes
from atrium.ingest.to_note_records import to_note_records
from atrium.store.delete_absent_conversations import delete_absent_conversations
from atrium.store.open_store import open_store
from atrium.store.write_conversation import UNCHANGED, write_conversation


def run_ingest_notes(  # noqa: PLR0913 -- the CLI surface: each argument is one flag
    index: Path,
    root: Path,
    provider: str,
    exclude: tuple[str, ...],
    *,
    sweep: bool = True,
    role: str = "note",
) -> int:
    """Index a notes tree, same transactional and sweep contract as `run_ingest`.

    ``role`` carries the origin mark: "note" for the user's own curated text,
    "source" for saved third-party content that must never be embedded or
    injected, only searched on request.
    """
    connection = open_store(index)
    total = 0
    files = 0
    unchanged = 0
    removed = 0
    tally = AdmissionTally()
    seen: set[str] = set()
    try:
        with connection:
            for note in read_notes(root, exclude, tally):
                files += 1
                tally.admit(role)
                written = write_conversation(
                    connection, note["path"], to_note_records(note, provider, role)
                )
                unchanged += written == UNCHANGED
                total += max(written, 0)
                seen.add(note["path"])
            if sweep:
                removed = delete_absent_conversations(connection, provider, seen)
    finally:
        connection.close()
    swept = f", {removed} absent removed" if removed else ""
    skipped = f", {unchanged} notes unchanged" if unchanged else ""
    print(f"  {files} notes -> {total} records written at {index}{skipped}{swept}")
    for label, counts in (("admitted", tally.admitted), ("rejected", tally.rejected)):
        if counts:
            ranked = sorted(counts.items(), key=lambda item: -item[1])
            plural = " files" if label == "rejected" else ""
            print(f"  {label}: " + ", ".join(f"{count:,} {name}{plural}" for name, count in ranked))
    return 0
