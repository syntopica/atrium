"""Whether a hit naming a retired term describes it as it was, not as it is."""

from atrium.context.retirement import Retirement
from atrium.retrieve.hit import Hit


def is_outdated_mention(hit: Hit, retirement: Retirement) -> bool:
    """History before the retirement date, or the declaring note's own history.

    Other curated notes are kept in place: they are edited by hand, and the
    measured ones already call the retired tool retired. An undated history
    record cannot show it postdates the retirement, so it counts as before.
    """
    if hit.role == "note":
        return hit.conversation_id == retirement.note
    return (hit.authored_at or "")[:10] < retirement.since
