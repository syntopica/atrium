"""Map each candidate that names a retired term to that retirement."""

from atrium.context.names_retirement import names_retirement
from atrium.context.retirement import Retirement
from atrium.retrieve.hit import Hit


def retired_mentions(
    candidates: list[tuple[Hit, str, str | None]], retirements: list[Retirement]
) -> dict[str, Retirement]:
    """Return record id to the first retirement its text names."""
    mentions: dict[str, Retirement] = {}
    for hit, _, _ in candidates:
        named = next((one for one in retirements if names_retirement(hit.text, one)), None)
        if named is not None:
            mentions[hit.record_id] = named
    return mentions
