"""One retrievable unit of memory."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Record:
    """A single retrievable passage, carrying enough provenance to be re-found.

    ``record_id`` is derived deterministically from the conversation and the
    event (see ``record_identity``), so two machines ingesting the same archive
    produce the same key without coordinating -- which is what lets each machine
    build its own index instead of copying one. The previous system paid five
    index rebuilds in 27 days for syncing a mutable index between two Macs.

    ``event_id`` is the archive's own identifier, kept for tracing back. It is
    deliberately NOT the key: it is not unique across conversations.

    ``source_sha256`` pins the exact revision of the conversation this passage came
    from. A citation resolves to that revision, never to a byte offset, so editing
    an earlier passage cannot silently repoint a citation at different evidence.
    """

    record_id: str
    event_id: str
    conversation_id: str
    source_sha256: str
    provider: str
    role: str
    text: str
    authored_at: str | None
    workspace: str | None
    title: str | None
    event_index: int
