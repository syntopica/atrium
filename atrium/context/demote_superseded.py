"""Move superseded candidates below every current one."""

from atrium.context.supersession import Supersession
from atrium.retrieve.hit import Hit


def demote_superseded(
    candidates: list[tuple[Hit, str, str | None]], supersessions: dict[str, Supersession]
) -> list[tuple[Hit, str, str | None]]:
    """Keep order within each group; drop nothing.

    What a record said before it was corrected is still history worth finding
    when nothing current answers, so it is ranked last rather than removed.
    """
    current = [one for one in candidates if one[0].record_id not in supersessions]
    return current + [one for one in candidates if one[0].record_id in supersessions]
