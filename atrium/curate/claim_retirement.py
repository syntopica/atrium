"""The retirement a claim describes as current, if any."""

from typing import Any

from atrium.context.names_retirement import names_retirement
from atrium.context.retirement import Retirement


def claim_retirement(claim: dict[str, Any], retirements: list[Retirement]) -> Retirement | None:
    """Return the first retirement the claim names and was last seen before.

    Same rule as forgetting: a claim last stated before the retirement date
    describes the retired thing as current, and proposing it for a page would
    put Holded back on the invoicing page. A later claim naming it is usually
    the migration itself, and stays.
    """
    seen = str(claim.get("last_seen") or "")
    return next(
        (
            one
            for one in retirements
            if seen < one.since and names_retirement(str(claim.get("text") or ""), one)
        ),
        None,
    )
