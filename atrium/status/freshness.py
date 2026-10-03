"""One instant in a status document: when, and how old at writing time."""

from typing import Any

from atrium.status.iso_utc import iso_utc


def freshness(at: float | None, now: float) -> dict[str, Any]:
    """Return ``{"at", "ageSeconds"}``, both null when the instant is unknown.

    The instant is the durable fact; the age is a convenience measured at
    ``writtenAt``, so a reader that wants the current age recomputes it from
    ``at`` rather than trusting a number that grows stale with the file.
    """
    if at is None:
        return {"at": None, "ageSeconds": None}
    return {"at": iso_utc(at), "ageSeconds": int(now - at)}
