"""Produce bounded excerpts centered on the query's actual evidence."""

import re


def matched_excerpt(text: str, query: str, budget: int) -> tuple[str, int, int]:
    """Prefer a complete exact identifier over prefix-only truncation."""
    if len(text) <= budget:
        return text, 0, len(text)
    matches = [
        re.search(re.escape(term), text, re.IGNORECASE) for term in [query.strip(), *query.split()]
    ]
    match = next((match for match in matches if match is not None), None)
    start = max(0, match.start() - max(0, (budget - len(match.group())) // 2)) if match else 0
    start = min(start, len(text) - budget)
    return text[start : start + budget], start, start + budget
