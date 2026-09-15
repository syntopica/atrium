"""Validate context requests before any index or model access."""

from atrium.retrieve.search import LANES


def validate_request(query: str, limit: int, max_chars: int, lane: str) -> None:
    """Reject empty queries and bounds that could silently become unlimited."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    for name, value, ceiling in (("limit", limit, 50), ("max_chars", max_chars, 100000)):
        if type(value) is not int or not 1 <= value <= ceiling:
            raise ValueError(f"{name} must be an integer between 1 and {ceiling}")
    if lane not in LANES:
        raise ValueError(f"unknown lane {lane!r}; expected one of {', '.join(LANES)}")
