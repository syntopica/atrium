"""Hits rendered whole for an MCP answer."""

import sqlite3
from typing import Any

from atrium.context.annotate_hosts import annotate_hosts
from atrium.context.render_hit import render_hit
from atrium.retrieve.hit import Hit


def rendered_hits(
    hits: list[Hit], *, connection: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    """Return whole hits.

    Never the CLI's printed form: that truncates text to fit a terminal, and an
    agent served the truncated version has no way to see what is missing.
    """
    items = [render_hit(hit) for hit in hits]
    if connection is not None:
        annotate_hosts(connection, items)
    return items
