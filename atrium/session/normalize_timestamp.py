"""One timestamp spelling: UTC, millisecond precision, ``Z``."""

from datetime import UTC, datetime


def normalize_timestamp(value: str) -> str | None:
    """Return ``value`` as the exporter writes it, or None when unparseable.

    rocket-agents stores `new Date(x).toISOString()`; an ISO string copied
    verbatim would sort `10:00+02:00` after `09:30Z` although it is earlier.
    """
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
