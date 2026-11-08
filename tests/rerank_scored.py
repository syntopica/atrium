"""How many candidates a context answer's rerank step scored, if it reranked."""

from typing import Any


def rerank_scored(response: dict[str, Any]) -> int | None:
    """Return the rerank step's ``scored`` count, or None when no rerank ran."""
    for step in response["steps"]:
        if step["pass"] == "rerank":
            return step["scored"]
    return None
