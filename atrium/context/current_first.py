"""Order candidates so what is current comes before what is retired or replaced."""

import sqlite3

from atrium.context.demote_retired import demote_retired
from atrium.context.demote_superseded import demote_superseded
from atrium.context.read_supersessions import read_supersessions
from atrium.context.retirement import Retirement
from atrium.retrieve.hit import Hit


def current_first(
    connection: sqlite3.Connection,
    candidates: list[tuple[Hit, str, str | None]],
    mentions: dict[str, Retirement],
    query: str,
) -> list[tuple[Hit, str, str | None]]:
    """Return the candidates reordered; nothing is dropped.

    Superseded records go last of all, after outdated mentions of retired
    things: a record a later statement corrected about this very subject is
    further from current than one that merely names a retired tool.
    """
    supersessions = read_supersessions(connection, [one[0].record_id for one in candidates])
    return demote_superseded(demote_retired(candidates, mentions, query), supersessions)
