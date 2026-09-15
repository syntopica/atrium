"""Follow one hop of safe curated links using only the selected index."""

import sqlite3

from atrium.context.link_targets import link_targets
from atrium.context.note_path import note_path
from atrium.retrieve.hit import Hit


def linked_hits(
    connection: sqlite3.Connection, roots: list[Hit], limit: int
) -> tuple[list[tuple[Hit, str]], list[str]]:
    """Follow direct roots only; cycles never enqueue another expansion."""
    found: list[tuple[Hit, str]] = []
    warnings: set[str] = set()
    seen = {hit.record_id for hit in roots}
    for root in roots:
        path = note_path(root.conversation_id)
        if path is None:
            warnings.add("invalid_note_path")
            continue
        for candidates in link_targets(root.text, path):
            if not candidates:
                warnings.add("unsafe_link_ignored")
                continue
            rows = []
            for candidate in candidates:
                rows = connection.execute(
                    "SELECT record_id, text, conversation_id, source_sha256, authored_at, provider, role FROM records WHERE role = 'note' AND provider = ? AND conversation_id = ? ORDER BY event_index, record_id LIMIT ?",
                    (root.provider, candidate, limit),
                ).fetchall()
                if rows:
                    break
            if not rows:
                warnings.add("unresolved_indexed_link")
            for row in rows:
                if row[0] in seen:
                    continue
                seen.add(row[0])
                found.append(
                    (
                        Hit(row[0], row[1], 0.0, "linked", row[2], row[3], row[4], row[5], row[6]),
                        root.record_id,
                    )
                )
                if len(found) >= limit:
                    return found, sorted(warnings)
    return found, sorted(warnings)
