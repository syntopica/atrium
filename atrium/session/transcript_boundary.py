"""The last eligible transcript record: where a session episode ends."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptBoundary:
    """A ``user`` or ``assistant`` record with a uuid and a timestamp.

    ``offset`` is the byte position just after the record's line, so bytes
    written after the boundary are ``size - offset`` without re-reading.
    """

    uuid: str
    timestamp: str
    offset: int
