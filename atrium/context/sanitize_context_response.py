"""Defend context adapters against unsanitized resident-service responses."""

from copy import deepcopy
from typing import Any

from atrium.session.redact_sensitive_text import redact_sensitive_text


def sanitize_context_response(response: dict[str, Any]) -> dict[str, Any]:
    """Redact full evidence; withhold legacy excerpts whose omitted labels are unknown.

    A resident process may predate the full-hit redaction code. Its truncated
    excerpt cannot be safely classified without its surrounding credential label.
    Offsets are withheld when adapter redaction changes an old response.
    """
    result = deepcopy(response)
    withheld = False
    for item in result.get("evidence", []):
        original = item.get("text", "")
        if item.get("truncated") and item.get("excerpt_basis") != "redacted_text":
            sanitized = "[REDACTED:unverified-excerpt]"
            withheld = True
        else:
            sanitized = redact_sensitive_text(original)
        # Never grow an already-budgeted response at the adapter boundary.
        item["text"] = sanitized[: len(original)]
        if item["text"] != original:
            item["excerpt_start"] = None
            item["excerpt_end"] = None
            item["excerpt_basis"] = "redacted_text"
        if isinstance(item.get("title"), str):
            item["title"] = redact_sensitive_text(item["title"])
    if withheld:
        result.setdefault("warnings", []).append("legacy_excerpt_withheld")
        result["degraded"] = True
    if "text_chars" in result:
        result["text_chars"] = sum(len(item.get("text", "")) for item in result.get("evidence", []))
    return result
