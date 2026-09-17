"""The bucket a candidate is sampled from."""

from typing import Any


def candidate_stratum(record: dict[str, Any]) -> str:
    """Return ``<month>/<repetition>`` for one ledger line.

    Both halves matter. The archive is not uniform in time -- the months with
    the heaviest work would otherwise swamp a sample -- and a claim stated by
    several episodes behaves differently from one stated once, which is
    exactly the difference stage three has to handle.
    """
    month = str(record.get("last_seen") or "unknown")[:7]
    repeated = "repeated" if int(record.get("episodes") or 1) > 1 else "single"
    return f"{month}/{repeated}"
