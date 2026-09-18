"""The schema a model fills when it places one claim on a curated page."""

from typing import Any

NO_DESTINATION = "NONE"


def destination_tool(paths: list[str]) -> dict[str, Any]:
    """Return the tool contract for one destination choice, closed over ``paths``.

    The enum is built per call rather than left open: a free-text answer invents
    page paths that do not exist, and a proposal against a missing page is worse
    than no proposal.
    """
    return {
        "name": "record_destination",
        "input_schema": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "enum": [*paths, NO_DESTINATION],
                    "description": (
                        "The page a reader looking for this fact later would open, or NONE."
                    ),
                },
                "why": {
                    "type": "string",
                    "description": "One sentence, quoting the page's scope or the fact itself.",
                },
            },
            "required": ["destination", "why"],
        },
    }
