"""Lossless provenance rendering shared with legacy retrieval tools."""

from dataclasses import asdict
from typing import Any

from atrium.context.trust_for_role import trust_for_role
from atrium.retrieve.hit import Hit
from atrium.session.redact_sensitive_text import redact_sensitive_text


def render_hit(hit: Hit) -> dict[str, Any]:
    """Preserve every hit field, including its security-relevant role."""
    result = {**asdict(hit), "trust": trust_for_role(hit.role)}
    for field in ("text", "title"):
        if isinstance(result.get(field), str):
            result[field] = redact_sensitive_text(result[field])
    return result
