"""Deduplicate and budget evidence shared by all retrieval passes."""

import unicodedata
from typing import Any

from atrium.context.render_evidence import render_evidence
from atrium.retrieve.hit import Hit


def select_evidence(
    candidates: list[tuple[Hit, str, str | None]], response: dict[str, Any]
) -> None:
    """Allocate a fair text share while respecting the total evidence count."""
    unique = []
    seen: set[str] = set()
    included_ids: set[str] = set()
    for hit, via, parent in candidates:
        if parent is not None and parent not in included_ids:
            if "linked_parent_deduplicated" not in response["warnings"]:
                response["warnings"].append("linked_parent_deduplicated")
            continue
        identity = " ".join(unicodedata.normalize("NFKC", hit.text).casefold().split())
        if identity in seen:
            response["deduplicated"] += 1
            continue
        seen.add(identity)
        included_ids.add(hit.record_id)
        unique.append((hit, via, parent))
    selected = unique[: min(response["limit"], response["max_chars"])]
    remaining = response["max_chars"]
    for position, (hit, via, parent) in enumerate(selected):
        item = render_evidence(
            hit, response["query"], remaining // (len(selected) - position), via, parent
        )
        response["evidence"].append(item)
        remaining -= len(item["text"])
    response["text_chars"] = response["max_chars"] - remaining
    response["truncated"] = len(selected) < len(unique) or any(
        item["truncated"] for item in response["evidence"]
    )
