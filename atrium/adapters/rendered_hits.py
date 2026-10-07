"""Hits rendered whole for an MCP answer."""

from typing import Any

from atrium.context.render_hit import render_hit
from atrium.retrieve.hit import Hit


def rendered_hits(hits: list[Hit]) -> list[dict[str, Any]]:
    """Return whole hits.

    Never the CLI's printed form: that truncates text to fit a terminal, and an
    agent served the truncated version has no way to see what is missing.
    """
    return [render_hit(hit) for hit in hits]
