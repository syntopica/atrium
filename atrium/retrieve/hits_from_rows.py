"""Turn the word lane's rows into hits, in the column order its query selects."""

from typing import Any

from atrium.retrieve.hit import Hit


def hits_from_rows(rows: list[Any]) -> list[Hit]:
    """Build hits from rows of (record_id, text, score, conversation, sha, at, provider, role)."""
    return [
        Hit(
            record_id=row[0],
            text=row[1],
            score=float(row[2]),
            lane="words",
            conversation_id=row[3],
            source_sha256=row[4],
            authored_at=row[5],
            provider=row[6],
            role=row[7],
        )
        for row in rows
    ]
