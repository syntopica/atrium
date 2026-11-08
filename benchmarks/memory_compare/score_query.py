"""Score one source-level query without granting partial answers full credit."""

from benchmarks.memory_compare.source_identity import source_identity


def score_query(row: dict, sources: list[str], available: set[str]) -> dict:
    """Deduplicate sources inside the fixed eight-record retrieval budget."""
    good = {row["answer_conversation_id"], *row.get("also_answers", [])}
    found = list(dict.fromkeys(source_identity(value) for value in sources[:8]))
    rank = next((index + 1 for index, value in enumerate(found) if value in good), None)
    return {
        "id": row["id"],
        "split": row["split"],
        "strata": row["strata"],
        "answerable": bool(good & available),
        "rank": rank,
    }
