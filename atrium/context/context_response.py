"""Build the common response envelope, including explicit unknown metadata."""

from pathlib import Path
from typing import Any

from atrium.context.context_configuration import context_configuration
from atrium.context.context_freshness import context_freshness


def context_response(  # noqa: PLR0913, PLR0917 -- mirrors the public request envelope
    query: str,
    project: str | Path | None,
    workspace: str | None,
    limit: int,
    max_chars: int,
    lane: str,
    state: Path | None,
) -> dict[str, Any]:
    """Start a response with no implicit claim about index health."""
    configuration = context_configuration(state)
    freshness = context_freshness(Path(configuration["state"]))
    warnings = [] if freshness["status"] == "fresh" else [f"refresh_{freshness['status']}"]
    if configuration["status"] in ("invalid", "missing"):
        warnings.append(f"configuration_{configuration['status']}")
    return {
        "query": query,
        "scope": {"project": str(project) if project is not None else None, "workspace": workspace},
        "route": {"requested_lane": lane, "history_lane": lane, "curated_lane": lane},
        "evidence": [],
        "steps": [],
        "freshness": freshness,
        "configuration": configuration,
        "index_status": "unknown",
        "degraded": bool(warnings),
        "warnings": warnings,
        "requires_live_verification": True,
        "limit": limit,
        "max_chars": max_chars,
        "text_chars": 0,
        "deduplicated": 0,
        "truncated": False,
    }
