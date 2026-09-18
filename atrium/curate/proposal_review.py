"""Render the one document a human reads before anything reaches the wiki."""

from typing import Any


def proposal_review(placed: dict[str, list[dict[str, Any]]], refused: list[dict[str, Any]]) -> str:
    """Return the review sheet: every destination, its claims, and what was refused.

    Markdown rather than JSON because this file is read by a person, and the
    decision it asks for - does this fact belong on this page - is not one a
    diff answers. The machine-readable copy is the manifest beside it.
    """
    lines = ["# Page proposals", ""]
    lines.append(
        f"{sum(len(rows) for rows in placed.values()):,} claims on {len(placed):,} pages, "
    )
    lines.append(f"{len(refused):,} refused a destination.")
    lines.append("")
    for page in sorted(placed, key=lambda path: (-len(placed[path]), path)):
        lines.append(f"## {page}")
        lines.append("")
        for row in placed[page]:
            lines.append(f"- {row['text']}")
            lines.append(f"  - why: {row['why']}")
            lines.append(
                f"  - seen: {row['first_seen']}..{row['last_seen']}"
                f" | episodes: {row['episodes']} | claim: `{row['candidate_id']}`"
            )
        lines.append("")
    if refused:
        lines.append("## Refused a destination")
        lines.append("")
        lines.append("Kept here rather than dropped: a refusal is evidence the shortlist")
        lines.append("missed a page, or that the claim was never wiki material.")
        lines.append("")
        for row in refused:
            lines.append(f"- {row['text']}")
            lines.append(f"  - shortlist: {', '.join(row['shortlist']) or 'empty'}")
        lines.append("")
    return "\n".join(lines)
