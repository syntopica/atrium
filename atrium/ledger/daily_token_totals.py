"""Records and tokens per UTC day over the last few days."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from atrium.ledger.read_record_file import read_record_file
from atrium.ledger.record_tokens import record_tokens
from atrium.ledger.record_written_at import record_written_at


def daily_token_totals(
    entries: list[tuple[float, Path]], now: float, days: int
) -> list[dict[str, Any]]:
    """Return one row per UTC day, oldest first, zero-filled.

    A day is when the registry gained the record, not when its conversation
    happened. Only files modified inside the window are opened, so the cost
    follows recent activity rather than the size of the registry.
    """
    today = datetime.fromtimestamp(now, UTC).date()
    first = today - timedelta(days=days - 1)
    start = datetime(first.year, first.month, first.day, tzinfo=UTC).timestamp()
    rows = {(first + timedelta(days=offset)).isoformat(): [0, 0, 0] for offset in range(days)}
    for mtime, path in entries:
        if mtime < start:
            continue
        record = read_record_file(path)
        if record is None:
            continue
        day = datetime.fromtimestamp(record_written_at(record, mtime), UTC).date().isoformat()
        row = rows.get(day)
        if row is None:
            continue
        input_tokens, output_tokens = record_tokens(record)
        row[0] += 1
        row[1] += input_tokens
        row[2] += output_tokens
    return [
        {"day": day, "records": row[0], "inputTokens": row[1], "outputTokens": row[2]}
        for day, row in rows.items()
    ]
