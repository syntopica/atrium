"""Turn one curated note into retrievable records."""

import re
from collections.abc import Iterator
from itertools import pairwise

from atrium.ingest.record_identity import record_identity
from atrium.record import Record

_HEADING = re.compile(r"^#{1,6}\s", re.MULTILINE)
# Chunks bounded so one section cannot monopolise a vector: the embedder
# truncates at 2,048 tokens, and a chunk far past that embeds only its head.
_MAX_CHUNK_CHARS = 2000


def to_note_records(note: dict, provider: str = "brain", role: str = "note") -> Iterator[Record]:
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
    title = _first_heading(text) or note["path"]
    chunks = [piece for section in _split_on_headings(text) for piece in _split_to_size(section)]
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


def _first_heading(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip() or None
    return None


def _split_on_headings(text: str) -> list[str]:
    starts = [match.start() for match in _HEADING.finditer(text)]
    if not starts:
        return [text.strip()] if text.strip() else []
    bounds = ([0] if starts[0] != 0 else []) + starts + [len(text)]
    sections = [text[a:b].strip() for a, b in pairwise(bounds)]
    return [section for section in sections if section]


def _split_to_size(section: str) -> list[str]:
    if len(section) <= _MAX_CHUNK_CHARS:
        return [section]
    pieces: list[str] = []
    current = ""
    for paragraph in section.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph.strip()
        if len(candidate) > _MAX_CHUNK_CHARS and current:
            pieces.append(current)
            current = paragraph.strip()
        else:
            current = candidate
    if current:
        pieces.append(current)
    return [slice_ for piece in pieces for slice_ in _hard_split(piece)]


def _hard_split(piece: str) -> list[str]:
    """Bound even a single unbroken paragraph.

    Paragraph packing alone let a 17,999-character table through (reproduced by
    review), and past the embedder's 2,048-token truncation the tail of such a
    chunk contributes nothing to its vector -- two long texts differing only in
    their tails embedded byte-identically. The cut is positional, so it stays
    deterministic across machines.
    """
    if len(piece) <= _MAX_CHUNK_CHARS:
        return [piece]
    return [
        piece[start : start + _MAX_CHUNK_CHARS] for start in range(0, len(piece), _MAX_CHUNK_CHARS)
    ]
