"""Render a bounded passage with explicit date and revision semantics."""

from datetime import datetime
from typing import Any

from atrium.context.matched_excerpt import matched_excerpt
from atrium.context.note_path import note_path
from atrium.context.render_hit import render_hit
from atrium.retrieve.hit import Hit


def render_evidence(
    hit: Hit, query: str, budget: int, via: str, parent: str | None
) -> dict[str, Any]:
    """Keep indexed provenance separate from present-day verification."""
    result = render_hit(hit)
    text, start, end = matched_excerpt(hit.text, query, budget)
    date_status = "unknown"
    if hit.authored_at:
        try:
            datetime.fromisoformat(hit.authored_at.replace("Z", "+00:00"))
            date_status = "known"
        except ValueError:
            date_status = "invalid"
    result.update(
        {
            "text": text,
            "note_path": note_path(hit.conversation_id) if hit.role == "note" else None,
            "date_status": date_status,
            "revision_kind": "indexed_note_revision"
            if hit.role == "note"
            else "indexed_source_revision",
            "truncated": start != 0 or end != len(hit.text),
            "excerpt_start": start,
            "excerpt_end": end,
            "via": via,
            "parent_record_id": parent,
        }
    )
    return result
