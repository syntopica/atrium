"""Evidence reduced to what must agree whatever order a rerank left it in."""

from typing import Any

_ORDER_FIELDS = ("score", "lane")


def unordered_evidence(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop rank-dependent fields and sort the items by record id."""
    items = [
        {key: value for key, value in item.items() if key not in _ORDER_FIELDS} for item in evidence
    ]
    return sorted(items, key=lambda item: item["record_id"])
