"""One retrievable unit of memory."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Record:
    """A single retrievable passage, carrying enough provenance to be re-found.

    Identity is content-addressed by the archive, not assigned here: two machines
    ingesting the same archive must produce the same ``record_id`` without
    coordinating, which is what lets each machine build its own index instead of
    copying one (the previous system paid five index rebuilds in 27 days for
    syncing a mutable index between two Macs).

    ``source_sha256`` pins the exact revision of the conversation this passage came
    from. A citation resolves to that revision, never to a byte offset, so editing
    an earlier passage cannot silently repoint a citation at different evidence.
    """

    record_id: str
    conversation_id: str
    source_sha256: str
    provider: str
    role: str
    text: str
    authored_at: str | None
    workspace: str | None
    title: str | None
    event_index: int
