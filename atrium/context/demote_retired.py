"""Move outdated mentions of retired things below every other candidate."""

from atrium.context.is_outdated_mention import is_outdated_mention
from atrium.context.names_retirement import names_retirement
from atrium.context.retirement import Retirement
from atrium.retrieve.hit import Hit


def demote_retired(
    candidates: list[tuple[Hit, str, str | None]],
    mentions: dict[str, Retirement],
    query: str,
) -> list[tuple[Hit, str, str | None]]:
    """Keep order within each group; leave everything in place when asked by name.

    Nothing is dropped. A question that names the retired thing is a question
    about its history -- where Holded's archive went, what a Holded invoice
    said -- and gets that history ranked as found.
    """
    asked = {one for one in mentions.values() if names_retirement(query, one)}

    def outdated(hit: Hit) -> bool:
        retirement = mentions.get(hit.record_id)
        return (
            retirement is not None
            and retirement not in asked
            and is_outdated_mention(hit, retirement)
        )

    current = [one for one in candidates if not outdated(one[0])]
    return current + [one for one in candidates if outdated(one[0])]
