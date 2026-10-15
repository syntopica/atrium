"""The query-log line one context answer leaves."""

from datetime import datetime
from typing import Any

from atrium.session.redact_sensitive_text import redact_sensitive_text


def query_event(response: dict[str, Any], entrypoint: str, now: datetime) -> dict[str, Any]:
    """Keep what gap detection and usage counts need, and no evidence text.

    The question is kept, through the archive's redaction: a gap is a question,
    but a question can carry a token, and this log is written and synced apart
    from the archive that would have redacted it. Evidence is kept by record id and score only, so
    the log never becomes a second copy of the index.
    """
    evidence = response.get("evidence") or []
    query = response.get("query")
    return {
        "ts": now.isoformat(),
        "entrypoint": entrypoint,
        "query": redact_sensitive_text(query) if isinstance(query, str) else query,
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
