"""Turn one curated note into retrievable records."""

from collections.abc import Iterator

from atrium.ingest.first_heading import first_heading
from atrium.ingest.record_identity import record_identity
from atrium.ingest.split_on_headings import split_on_headings
from atrium.ingest.split_to_size import split_to_size
from atrium.record import Record


def to_note_records(
    note: dict[str, str], provider: str = "brain", role: str = "note"
) -> Iterator[Record]:
    """Yield one record per chunk of a note, split on headings then paragraphs.

    ``conversation_id`` is the note's relative path and ``event_id`` the chunk's
    position, so two machines chunking the same revision derive identical record
    ids -- the same convergence property the conversation path has. Editing a
    note shifts its chunks; reconciliation replaces the whole file's records, so
    stale chunks never linger.

    ``role`` is the origin mark, and it is security-relevant: "note" is the
    user's own curated text and earns a vector; "source" is saved third-party
    content (web articles), which stays out of SEMANTIC_ROLES so it is never
    embedded, never fused into semantic answers, and never injected at session
    start. It remains word- and substring-searchable when the user asks.
    """
    text = note["text"]
    title = first_heading(text) or note["path"]
    chunks = [piece for section in split_on_headings(text) for piece in split_to_size(section)]
    for index, chunk in enumerate(chunks):
        yield Record(
            record_id=record_identity(note["path"], f"chunk-{index:04d}"),
            event_id=f"chunk-{index:04d}",
            conversation_id=note["path"],
            source_sha256=note["sha256"],
            provider=provider,
            role=role,
            text=chunk,
            authored_at=None,
            workspace=None,
            title=title,
            event_index=index,
        )
