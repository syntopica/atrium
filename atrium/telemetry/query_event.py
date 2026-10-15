"""The query-log line one context answer leaves."""

from datetime import datetime
from typing import Any


def query_event(response: dict[str, Any], entrypoint: str, now: datetime) -> dict[str, Any]:
    """Keep what gap detection and usage counts need, and no evidence text.

    The question is kept verbatim: a gap is a question, and the archive holds
    the same words already. Evidence is kept by record id and score only, so
    the log never becomes a second copy of the index.
    """
    evidence = response.get("evidence") or []
    return {
        "ts": now.isoformat(),
        "entrypoint": entrypoint,
        "query": response.get("query"),
        "workspace": (response.get("scope") or {}).get("workspace"),
        "lane": (response.get("route") or {}).get("requested_lane"),
        "index_status": response.get("index_status"),
        "served_by": response.get("served_by"),
        "evidence": [
            {
                "record_id": item.get("record_id"),
                "score": item.get("score"),
                "lane": item.get("lane"),
                "via": item.get("via"),
            }
            for item in evidence
        ],
        "warnings": list(response.get("warnings") or []),
    }
