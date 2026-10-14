"""Describe each retrieval pass of one context answer: scope, lane, yield and time."""

from typing import Any


def context_steps(  # noqa: PLR0913 -- one figure per pass, all of them reported
    response: dict[str, Any],
    workspace: str | None,
    depth: int,
    limit: int,
    *,
    counts: tuple[int, int, int],
    times: tuple[int, int, int],
) -> list[dict[str, Any]]:
    """Return the history, curated and links steps in that order."""
    history, notes, links = counts
    history_ms, curated_ms, links_ms = times
    return [
        {
            "pass": "history",
            "scope": workspace or "all_history_explicit_unscoped",
            "lane": response["route"]["history_lane"],
            "candidates": history,
            "candidate_limit": depth,
            "ms": history_ms,
        },
        {
            "pass": "curated",
            "scope": "curated_notes_in_selected_index",
            "lane": response["route"]["curated_lane"],
            "candidates": notes,
            "candidate_limit": depth,
            "ms": curated_ms,
        },
        {
            "pass": "links",
            "scope": "one_hop_indexed_curated_same_provider",
            "lane": "linked",
            "candidates": links,
            "candidate_limit": depth,
            "root_limit": limit,
            "targets_per_root_limit": 50,
            "ms": links_ms,
        },
    ]
