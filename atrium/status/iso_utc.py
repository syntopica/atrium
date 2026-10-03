"""Render an epoch time the way every status document spells instants."""

from datetime import UTC, datetime


def iso_utc(seconds: float) -> str:
    """Return ISO 8601 UTC with a ``Z`` suffix, to the second."""
    moment = datetime.fromtimestamp(seconds, UTC).replace(microsecond=0)
    return moment.isoformat().replace("+00:00", "Z")
