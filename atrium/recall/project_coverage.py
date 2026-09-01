"""How many real projects have synthesized memory, and how many do not."""

import sqlite3
from typing import Any

# A workspace is any directory a session was opened in, so most of them are not
# projects: 13,162 of 13,269 held fewer than five conversations on 2026-09-01.
# Counting those makes coverage read 2.1% when the work that matters is above
# half, which is the difference between a number that informs a decision and
# one that only alarms.
DEFAULT_FLOOR = 20

_QUERY = """
SELECT workspace,
       count(DISTINCT CASE WHEN provider != 'synthesis' THEN conversation_id END) AS conversations,
       count(CASE WHEN provider = 'synthesis' THEN 1 END) AS episodes
FROM records
WHERE workspace IS NOT NULL AND provider != 'brain'
GROUP BY workspace
"""


def project_coverage(connection: sqlite3.Connection, floor: int = DEFAULT_FLOOR) -> dict[str, Any]:
    """Return coverage over projects holding at least ``floor`` conversations.

    ``uncovered`` names the largest projects with no memory at all, because
    "which of my real projects would recall answer nothing for" is the question
    this number exists to answer.
    """
    projects = [
        (workspace, conversations, episodes)
        for workspace, conversations, episodes in connection.execute(_QUERY)
        if conversations >= floor
    ]
    covered = [row for row in projects if row[2] > 0]
    uncovered = sorted((row for row in projects if row[2] == 0), key=lambda r: -r[1])
    return {
        "floor": floor,
        "projects": len(projects),
        "covered": len(covered),
        "uncovered": [(workspace, conversations) for workspace, conversations, _ in uncovered[:5]],
    }
