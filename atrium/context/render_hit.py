"""Lossless provenance rendering shared with legacy retrieval tools."""

from dataclasses import asdict
from typing import Any

from atrium.context.trust_for_role import trust_for_role
from atrium.retrieve.hit import Hit


def render_hit(hit: Hit) -> dict[str, Any]:
    """Preserve every hit field, including its security-relevant role."""
    return {**asdict(hit), "trust": trust_for_role(hit.role)}
