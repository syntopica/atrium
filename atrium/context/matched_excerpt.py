"""Produce bounded excerpts centered on the query's actual evidence."""

import re

from atrium.context.folded_text_offsets import folded_text_offsets
from atrium.retrieve.search_words import _fold


def matched_excerpt(text: str, query: str, budget: int) -> tuple[str, int, int]:
    """Prefer a complete exact identifier over prefix-only truncation."""
    if len(text) <= budget:
        return text, 0, len(text)
    normalized, offsets = folded_text_offsets(text)
    matches = [
        re.search(re.escape(_fold(term)), normalized, re.IGNORECASE)
        for term in [query.strip(), *query.split()]
        if _fold(term)
    ]
    match = next((match for match in matches if match is not None), None)
    start = 0
    if match is not None:
        match_start = offsets[match.start()]
        match_end = offsets[match.end() - 1] + 1
        start = max(0, match_start - max(0, (budget - (match_end - match_start)) // 2))
    start = min(start, len(text) - budget)
    return text[start : start + budget], start, start + budget
