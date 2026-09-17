"""Resolve which workspace each conversation was held in, from the index."""

import sqlite3
from pathlib import Path


def conversation_workspaces(index: Path, conversation_ids: list[str]) -> dict[str, str]:
    """Map conversation id to its dominant workspace, skipping what is unknown.

    The synthesis record does not carry a workspace -- it names the episode and
    the model, nothing about where the work happened -- so the project a claim
    belongs to has to be joined back through the index. Taking the most
    frequent workspace of a conversation rather than the first handles the
    sessions that begin in one directory and move.
    """
    if not conversation_ids or not index.exists():
        return {}
    found: dict[str, tuple[int, str]] = {}
    connection = sqlite3.connect(f"file:{index}?mode=ro", uri=True)
    try:
        for start in range(0, len(conversation_ids), 500):
            batch = conversation_ids[start : start + 500]
            placeholders = ",".join("?" * len(batch))
            # The only interpolation is a run of "?" placeholders built from the
            # batch length; every value is still bound.
            rows = connection.execute(
                "SELECT conversation_id, workspace, COUNT(*) FROM records "  # noqa: S608
                f"WHERE conversation_id IN ({placeholders}) AND workspace IS NOT NULL "
                "GROUP BY conversation_id, workspace",
                batch,
            )
            for conversation_id, workspace, count in rows:
                best = found.get(conversation_id)
                if best is None or count > best[0]:
                    found[conversation_id] = (count, workspace)
    finally:
        connection.close()
    return {conversation_id: workspace for conversation_id, (_, workspace) in found.items()}
